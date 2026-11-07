import { createContext,useContext,useEffect,useState,type ReactNode } from 'react';
import { api,type Brand } from '../api/client';
import { useAuth } from '../auth/AuthContext';
interface Workspace {brands:Brand[];brandId:string;setBrandId:(value:string)=>void;refresh:()=>Promise<void>}
const Context=createContext<Workspace|null>(null);
export function useWorkspace(){const value=useContext(Context);if(!value)throw new Error('Workspace provider missing');return value;}
export function WorkspaceProvider({children}:{children:ReactNode}){
  const {user}=useAuth();const key='mindvault.brand.'+user!.org_id;
  const [brands,setBrands]=useState<Brand[]>([]);const [brandId,setSelected]=useState(()=>{try{return sessionStorage.getItem(key)||'';}catch{return '';}});
  async function refresh(){const values=await api.request<Brand[]>('/brands');setBrands(values);setSelected(current=>values.some(b=>b.id===current)?current:values[0]?.id??'');}
  useEffect(()=>{void refresh().catch(()=>{});},[]);
  function setBrandId(value:string){setSelected(value);try{sessionStorage.setItem(key,value);}catch{/* Selection remains usable. */}}
  return <Context.Provider value={{brands,brandId,setBrandId,refresh}}>{children}</Context.Provider>;
}
