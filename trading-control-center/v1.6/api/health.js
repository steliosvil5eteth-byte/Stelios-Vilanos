import {authConfigured} from './_lib/session.js';
import {persistentStoreConfigured,storageBackend} from './_lib/store.js';
import {databaseConfigured} from './_lib/db.js';
import {billingConfig} from './_lib/billing.js';
import {emailConfig} from './_lib/email.js';
import {marketDataConfig} from './_lib/market-data.js';
import {getSafetyState} from './_lib/safety.js';
import {requestId} from './_lib/request-trace.js';
import {schemaStatus,APP_VERSION} from './_lib/release.js';
import {getMaintenanceState} from './_lib/maintenance.js';
export default async function handler(req,res){if(req.method!=='GET')return res.status(405).json({error:'GET only'});const rid=requestId(req,res),billing=billingConfig(),email=emailConfig(),marketData=marketDataConfig(),safety=await getSafetyState(),maintenance=await getMaintenanceState(),schema=await schemaStatus();res.setHeader('Cache-Control','no-store');res.status(200).json({version:APP_VERSION,paperOnly:true,auth:authConfigured(),store:persistentStoreConfigured(),storageBackend:storageBackend(),database:databaseConfigured(),rateLimiting:true,csrfProtection:true,versionedConsent:true,usageMetering:true,selfServiceDataExport:true,selfServiceDeletion:true,securityEvents:true,passwordReset:true,emailVerification:true,emailRecovery:true,onboarding:true,backupExport:true,monitoring:true,monitoringAlerts:true,billingReady:true,billingEnabled:billing.enabled,billingTestMode:billing.testMode,emailConfigured:email.configured,marketData:marketData.alphaConfigured||marketData.twelveConfigured,marketDataProviders:marketData,idempotentOrders:true,webhookReplayProtection:true,forwardSignalLedger:true,globalPaperKillSwitch:true,staleMarketDataGuard:true,brokerReconciliation:true,requestTracing:true,schemaValidation:true,maintenanceMode:true,dataIntegrityChecks:true,backupVerification:true,predeploySelfTest:true,schemaVersioning:true,ibkrWhatIf:Boolean(process.env.IBKR_BASE_URL&&process.env.IBKR_ACCOUNT_ID),multiUser:true,plans:true,adminDashboard:true,strategyLibrary:true,performanceReports:true,scheduledResearch:true,portfolioRisk:true,strategyLifecycle:true,equityCurve:true,safety,maintenance,schema,requestId:rid,liveExecution:false})}
