import { NextResponse } from 'next/server';
export const dynamic='force-dynamic';
export async function GET() {
  if(process.env.OIL_TEST_MODE==='1') {
    const {lei}=await import('../../../../mocks/lei');
    return NextResponse.json({disponivel:true,dados:lei,simulada:true});
  }
  // O3 ainda não foi entregue. Não adivinha rota/IDs, não usa mock como fallback.
  return NextResponse.json({disponivel:false,motivo:'Dado ainda não disponível',dados:null,simulada:false});
}
