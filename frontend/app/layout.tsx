import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'Observatório de Impacto Legislativo — Trabalho',description:'Fontes oficiais, séries históricas e leitura descritiva do mercado de trabalho.'};
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="pt-BR"><body>{children}</body></html>; }
