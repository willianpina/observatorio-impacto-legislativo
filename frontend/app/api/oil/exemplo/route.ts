import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
// Somente exemplos de vigência e votações, ausentes do contrato legislativo atual.
export async function GET(){
  if(process.env.OIL_TEST_MODE!=='1')return NextResponse.json({disponivel:false,motivo:'Exemplos indisponíveis no modo normal.',simulada:false},{status:404});
  const {lei}=await import('../../../../mocks/lei');
  return NextResponse.json({disponivel:true,dados:lei,simulada:true},{headers:{'Cache-Control':'no-store'}});
}
