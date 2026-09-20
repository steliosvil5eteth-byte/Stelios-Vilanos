import {getReleaseControl} from './release-control.js';
import {sloSnapshot} from './slo.js';
import {getIncidentState} from './incident.js';
import {getMaintenanceState} from './maintenance.js';
import {getSafetyState} from './safety.js';
export async function promotionGate({minSamples=3,targetAvailability=99.0}={}){const [release,slo,incident,maintenance,safety]=await Promise.all([getReleaseControl(),sloSnapshot({targetAvailability}),getIncidentState(),getMaintenanceState(),getSafetyState()]);const checks={releaseUnlocked:release.releaseLock===false,canaryMode:release.channel==='canary',canaryComplete:release.canaryPercent>=100,noActiveIncident:!incident.active,maintenanceEnabled:maintenance.enabled===true,emergencyStop:safety.emergencyStop===true,sloEnoughSamples:slo.samples>=minSamples,sloMeeting:slo.samples<minSamples?false:slo.status==='MEETING',liveExecutionOff:true};const ready=Object.values(checks).every(Boolean);return {ready,checks,release,slo,incident,maintenance,safety,checkedAt:new Date().toISOString()}}
