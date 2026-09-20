import {databaseConfigured,db} from './db.js';
export const APP_VERSION='1.7';
export const REQUIRED_SCHEMA_VERSION=4;
export async function schemaStatus(){if(!databaseConfigured())return {configured:false,current:null,required:REQUIRED_SCHEMA_VERSION,ok:false};try{const sql=await db();const rows=await sql`select value from tcc_meta where key='schema_version' limit 1`;const current=Number(rows[0]?.value||0);return {configured:true,current,required:REQUIRED_SCHEMA_VERSION,ok:current>=REQUIRED_SCHEMA_VERSION}}catch(e){return {configured:true,current:null,required:REQUIRED_SCHEMA_VERSION,ok:false,error:e.message}}}
