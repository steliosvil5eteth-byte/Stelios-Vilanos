import {getJson,setJson,appendAudit} from './store.js';

const KEY='tcc:system:safety';

function envEnabled(name,def=false){
  const raw=process.env[name];
  if(raw==null||raw==='') return def;
  return String(raw).toLowerCase()==='true';
}

export async function getSafetyState(){
  const saved=(await getJson(KEY))||{};
  const envPaper=envEnabled('PAPER_EXECUTION_ENABLED',false);
  const adminPaper=saved.paperExecutionEnabled===true;
  const emergencyStop=saved.emergencyStop!==false;
  return {
    paperExecutionEnvEnabled:envPaper,
    paperExecutionAdminEnabled:adminPaper,
    emergencyStop,
    paperExecutionAllowed:envPaper&&adminPaper&&!emergencyStop,
    reason:!envPaper?'PAPER_EXECUTION_ENV_DISABLED':!adminPaper?'PAPER_EXECUTION_ADMIN_DISABLED':emergencyStop?'EMERGENCY_STOP':'ALLOWED',
    updatedAt:saved.updatedAt||null,
    updatedBy:saved.updatedBy||null,
    note:String(saved.note||'').slice(0,240),
    liveExecution:false
  };
}

export async function updateSafetyState(user,{paperExecutionEnabled,emergencyStop,note}={}){
  const current=(await getJson(KEY))||{};
  const next={
    ...current,
    paperExecutionEnabled:paperExecutionEnabled===undefined?current.paperExecutionEnabled:paperExecutionEnabled===true,
    emergencyStop:emergencyStop===undefined?(current.emergencyStop!==false):emergencyStop===true,
    note:note===undefined?current.note:String(note||'').slice(0,240),
    updatedAt:new Date().toISOString(),
    updatedBy:String(user||'').slice(0,80)
  };
  await setJson(KEY,next);
  await appendAudit(user,{ts:next.updatedAt,type:'SYSTEM_SAFETY_UPDATE',detail:`paper=${next.paperExecutionEnabled===true} emergencyStop=${next.emergencyStop===true}`});
  return getSafetyState();
}

export async function requirePaperExecutionAllowed(){
  const s=await getSafetyState();
  if(!s.paperExecutionAllowed){
    const e=new Error(`Paper execution blocked: ${s.reason}`);
    e.status=423;e.code='PAPER_EXECUTION_BLOCKED';e.safety=s;throw e;
  }
  return s;
}
