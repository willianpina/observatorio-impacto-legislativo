"""Coleta legislativa independente das requisições da tela."""
import asyncio
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .catalog import PROPOSICOES
from .ingest import SourceFailure, retry_delay
from .models import Coleta, Fonte, Marco, Proposicao, ProposicaoSnapshot
from .law_schemas import GeneratedNorm


def endpoints(identifier):
    senate = PROPOSICOES[identifier]['id_senado']
    return {'camara': f'https://dadosabertos.camara.leg.br/api/v2/proposicoes/{identifier}',
            'senado': f'https://legis.senado.leg.br/dadosabertos/processo/{senate}?v=1'}


def public_link(identifier, house):
    return (f'https://www.camara.leg.br/propostas-legislativas/{identifier}' if house == 'camara'
            else endpoints(identifier)['senado'])


def instant(value):
    parsed = datetime.fromisoformat(value)
    # A data legislativa sem fuso é uma data civil no Brasil, nunca hora de coleta.
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def stage(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if not unicodedata.combining(c))
    if 'norma juridica' in text:
        return 'norma_juridica'
    return ' '.join(text.split())


class LawCollector:
    def __init__(self, sessions, client, *, simulada=False, sleep=asyncio.sleep):
        if simulada and os.environ.get('OIL_TEST_MODE') != '1':
            raise ValueError('Coleta simulada exige modo de teste explícito.')
        self.sessions, self.client, self.simulada, self.sleep = sessions, client, simulada, sleep

    def record(self, identifier, house, url, response=None, error=None, kind='legislacao'):
        with self.sessions.begin() as session:
            code = house + '-dados-abertos'
            session.execute(insert(Fonte).values(codigo=code,
                nome='Câmara dos Deputados' if house == 'camara' else 'Senado Federal',link=url)
                .on_conflict_do_nothing(index_elements=['codigo']))
            raw = response.content if response is not None else None
            collection = Coleta(fonte_id=session.scalar(select(Fonte.id).where(Fonte.codigo == code)),
                serie_codigo=f'proposicao:{identifier}:{house}', url_consultada=url,
                coletado_em=datetime.now(timezone.utc),codigo_http=response.status_code if response is not None else None,
                resposta_bruta=raw,hash_sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None,
                simulada=self.simulada,erro=error,tipo=kind,valida=False)
            session.add(collection); session.flush()
            return collection.id

    async def fetch(self, identifier, house, url, *, kind='legislacao'):
        for attempt in range(3):
            response = None
            try:
                response = await self.client.get(url)
            except httpx.TimeoutException:
                failure = SourceFailure('timeout_fonte',504)
                self.record(identifier,house,url,error=failure.code,kind=kind)
            except httpx.TransportError:
                failure = SourceFailure('erro_conexao',503)
                self.record(identifier,house,url,error=failure.code,kind=kind)
            else:
                ok = response.status_code == 200
                failure = SourceFailure('http_fonte',503 if response.status_code in {429,500,502,503,504} else 502)
                cid = self.record(identifier,house,url,response,None if ok else failure.code,kind)
                if ok:
                    try:
                        return response.json(),cid
                    except ValueError:
                        with self.sessions.begin() as session:
                            session.get(Coleta,cid).erro='resposta_invalida'
                        raise SourceFailure('resposta_invalida') from None
                if failure.status != 503:
                    raise failure
            if attempt < 2:
                await self.sleep(retry_delay(response,attempt))
        raise failure

    async def authors(self, identifier, url):
        missing = dict(autor=None,partido=None,uf=None,partido_referencia=None,coautores=None,
                       autoria_motivo='Autoria não informada pela fonte.',_coletas_autoria=[])
        try:
            payload,authors_id = await self.fetch(identifier,'camara',url+'/autores',kind='autoria')
            missing['_coletas_autoria']=[authors_id]
            authors = payload['dados']
            principal = next((a for a in authors if a.get('ordemAssinatura') == 1),None)
            if principal is None:
                return missing
            result = dict(missing,autor=principal.get('nome'),coautores=max(len(authors)-1,0))
            uri = principal.get('uri','')
            # Não segue URIs arbitrárias recebidas da fonte.
            if re.fullmatch(r'https://dadosabertos\.camara\.leg\.br/api/v2/deputados/[0-9]+',uri):
                deputy,deputy_id = await self.fetch(identifier,'camara',uri,kind='autoria')
                result['_coletas_autoria'].append(deputy_id)
                status = deputy['dados'].get('ultimoStatus',{})
                result.update(partido=status.get('siglaPartido'),uf=status.get('siglaUf'),
                    partido_referencia='atual',autoria_motivo='Partido e UF atuais; referência histórica não publicada nesta consulta.')
            return result
        except (SourceFailure,ValueError,TypeError,KeyError):
            return missing

    async def collect(self, identifier):
        if identifier not in PROPOSICOES:
            raise ValueError('Proposição não acompanhada.')
        failures = []
        for house,url in endpoints(identifier).items():
            cid = None
            try:
                payload,cid = await self.fetch(identifier,house,url)
                if house == 'camara':
                    data = payload['dados']; status = data['statusProposicao']
                    if data['id'] != identifier: raise ValueError('Identificador divergente.')
                    if not isinstance(data['siglaTipo'],str) or not isinstance(data['ementa'],str):
                        raise ValueError('Identificação legislativa inválida.')
                    int(data['numero']);int(data['ano'])
                    normalized = dict(ementa=data['ementa'],situacao_texto=status['descricaoSituacao'],
                        situacao_data=instant(status['dataHora']),norma_json=None,
                        autor_json=dict(await self.authors(identifier,url),data_apresentacao=data['dataApresentacao'],
                            _identificacao={'sigla_tipo':data['siglaTipo'],'numero':int(data['numero']),'ano':int(data['ano'])}))
                else:
                    if payload['id'] != PROPOSICOES[identifier]['id_senado']: raise ValueError('Identificador divergente.')
                    norm=payload.get('normaGerada') or None
                    if norm:
                        GeneratedNorm.model_validate(dict(norm,fonte=url))
                    normalized = dict(ementa=payload.get('conteudo',{}).get('ementa'),
                        situacao_texto=payload['situacaoAtual'],situacao_data=instant(payload['dataSituacaoAtual']),
                        norma_json=norm,autor_json={})
                if not isinstance(normalized['situacao_texto'],str) or not normalized['situacao_texto'].strip():
                    raise ValueError('Situação ausente.')
                self.persist(identifier,house,payload,normalized,cid)
            except (SourceFailure,ValueError,TypeError,KeyError,AttributeError) as exc:
                failure = exc if isinstance(exc,SourceFailure) else SourceFailure('resposta_invalida')
                if cid is not None:
                    with self.sessions.begin() as session:
                        session.get(Coleta,cid).erro = failure.code
                failures.append(failure)
        if len(failures) == 2:
            raise failures[-1]
        return {'id_camara':identifier,'simulada':self.simulada}

    def persist(self, identifier, house, payload, values, cid):
        with self.sessions.begin() as session:
            session.execute(insert(Proposicao).values(id_camara=identifier,id_senado=PROPOSICOES[identifier]['id_senado'])
                .on_conflict_do_nothing(index_elements=['id_camara']))
            prop = session.scalar(select(Proposicao).where(Proposicao.id_camara==identifier).with_for_update())
            if house == 'camara':
                data=payload['dados']; prop.sigla_tipo=data['siglaTipo']; prop.numero=int(data['numero']); prop.ano=int(data['ano'])
            old = session.scalar(select(ProposicaoSnapshot).join(Coleta).where(
                ProposicaoSnapshot.proposicao_id==prop.id,ProposicaoSnapshot.casa==house,
                Coleta.simulada==self.simulada).order_by(ProposicaoSnapshot.versao.desc()).limit(1))
            link=public_link(identifier,house)
            if house=='senado' and isinstance(payload.get('codigoMateria'),int):
                link=f'https://www25.senado.leg.br/web/atividade/materias/-/materia/{payload["codigoMateria"]}'
            fields=dict(values,link=link)
            def comparable(key,value):
                return {k:v for k,v in value.items() if k!='_coletas_autoria'} if key=='autor_json' else value
            changed = old is None or any(comparable(key,getattr(old,key))!=comparable(key,value) for key,value in fields.items())
            if changed:
                version = session.scalar(select(ProposicaoSnapshot.versao).where(
                    ProposicaoSnapshot.proposicao_id==prop.id,ProposicaoSnapshot.casa==house)
                    .order_by(ProposicaoSnapshot.versao.desc()).limit(1)) or 0
                session.add(ProposicaoSnapshot(proposicao_id=prop.id,casa=house,coleta_id=cid,versao=version+1,**fields))
            session.get(Coleta,cid).valida=True
            if house == 'senado':
                deliberation=payload.get('deliberacao',{})
                markers=[]
                if deliberation.get('siglaTipo')=='APROVADA_NO_PLENARIO':
                    markers.append(('aprovacao_senado',deliberation['tipoDeliberacao'],deliberation['data']))
                if stage(values['situacao_texto'])=='norma_juridica':
                    markers.append(('promulgacao',values['situacao_texto'],values['situacao_data'].date().isoformat()))
                for kind,label,date in markers:
                    marker=session.scalar(select(Marco).where(Marco.proposicao_id==prop.id,Marco.tipo==kind,Marco.simulada==self.simulada))
                    if marker is None:
                        marker=Marco(proposicao_id=prop.id,tipo=kind,simulada=self.simulada);session.add(marker)
                    marker.rotulo=label;marker.data=date;marker.prevista=False;marker.coleta_id=cid
                    marker.fonte=endpoints(identifier)[house];marker.link=link;marker.origem='fonte';marker.artigo=None


def read_law(session, identifier, *, test_mode=False):
    if identifier not in PROPOSICOES:
        raise HTTPException(404,'Proposição não acompanhada.')
    prop=session.scalar(select(Proposicao).where(Proposicao.id_camara==identifier))
    statuses=[]; snapshots={}; latest_good=[]; failures=[]; stale=False
    for house,url in endpoints(identifier).items():
        collections=session.scalars(select(Coleta).where(Coleta.serie_codigo==f'proposicao:{identifier}:{house}',
            Coleta.simulada==test_mode,Coleta.tipo=='legislacao').order_by(Coleta.id.desc())).all()
        good=next((c for c in collections if c.valida),None)
        failed=next((c for c in collections if c.erro),None)
        if failed: failures.append(failed)
        snap=session.scalar(select(ProposicaoSnapshot).join(Coleta).where(
            ProposicaoSnapshot.proposicao_id==prop.id,ProposicaoSnapshot.casa==house,
            Coleta.simulada==test_mode,Coleta.valida.is_(True)).order_by(ProposicaoSnapshot.versao.desc()).limit(1)) if prop else None
        available=good is not None and (failed is None or failed.id<good.id)
        stale=stale or (good is not None and not available)
        if good: latest_good.append(good)
        if snap: snapshots[house]=snap
        statuses.append(dict(casa=house,situacao=snap.situacao_texto if snap else 'não informado',
            data=snap.situacao_data.date().isoformat() if snap else None,link=snap.link if snap else public_link(identifier,house),fonte=url,
            coleta_id=good.id if good else None,coletado_em=good.coletado_em.isoformat() if good else None,
            disponivel=available,motivo=None if available else 'Fonte temporariamente indisponível.'))
    if not latest_good:
        failure=max(failures,key=lambda c:c.id) if failures else None
        status=504 if failure and failure.erro=='timeout_fonte' else 503 if failure is None or failure.erro=='erro_conexao' or failure.codigo_http in {429,500,502,503,504} else 502
        raise SourceFailure(failure.erro if failure else 'sem_coleta_valida',status)
    candidates=[s for s in statuses if s['disponivel']] or [s for s in statuses if s['coleta_id']]
    chosen=max(candidates,key=lambda s:(snapshots[s['casa']].situacao_data,s['casa']=='senado'))
    divergent=len(snapshots)==2 and len({stage(s.situacao_texto) for s in snapshots.values()})>1
    current=dict(chosen,regra='mais_recente' if len(candidates)==2 else 'unica_disponivel',divergencia=divergent)
    chamber=snapshots.get('camara');senate=snapshots.get('senado')
    authors=dict(chamber.autor_json) if chamber else dict(autor=None,partido=None,uf=None,coautores=None,partido_referencia=None,data_apresentacao=None,autoria_motivo='Autoria não disponível.')
    identity=authors.pop('_identificacao',{'sigla_tipo':None,'numero':None,'ano':None})
    authors.pop('_coletas_autoria',None)
    norm=dict(senate.norma_json,fonte=endpoints(identifier)['senado']) if senate and senate.norma_json else None
    markers=session.scalars(select(Marco).join(Coleta).where(Marco.proposicao_id==prop.id,Coleta.simulada==test_mode,
        Coleta.valida.is_(True)).order_by(Marco.data,Marco.tipo)).all()
    sources=json.loads((Path(__file__).parents[1]/'data/fontes_norma.json').read_text(encoding='utf-8'))
    last=max(latest_good,key=lambda c:c.id)
    return dict(id_camara=identifier,id_senado=PROPOSICOES[identifier]['id_senado'],**identity,
        ementa=chamber.ementa if chamber else None,**authors,
        situacao=statuses,situacao_atual=current,norma_gerada=norm,
        norma_gerada_motivo=None if norm else 'normaGerada vazio ou não disponível na fonte do Senado',
        marcos=[{key:getattr(m,key) for key in ('tipo','rotulo','data','prevista','fonte','link','origem','artigo')} for m in markers],
        fontes_norma=sources,nivel_evidencia='descritivo',desatualizado=stale,simulada=test_mode,
        fonte='Câmara dos Deputados / Senado Federal',coleta_id=last.id,coletado_em=last.coletado_em.isoformat())
