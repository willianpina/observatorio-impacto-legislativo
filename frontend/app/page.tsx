import Dashboard from '../components/dashboard';
export const dynamic='force-dynamic';
export default function Page(){ return <Dashboard testMode={process.env.OIL_TEST_MODE==='1'}/>; }
