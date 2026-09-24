import assert from 'node:assert/strict';
import {parseAlphaNews,parseSecSubmissions,combineTechnicalAndEvent} from '../api/_lib/event-data.js';

const now=new Date('2026-09-25T12:00:00Z');
const alpha={feed:[
  {title:'Company raises outlook after strong demand',url:'https://example.com/a',source:'SourceA',time_published:'20260925T113000',ticker_sentiment:[{ticker:'TEST',relevance_score:'0.95',ticker_sentiment_score:'0.45',ticker_sentiment_label:'Bullish'}]},
  {title:'Analysts react to guidance',url:'https://example.com/b',source:'SourceB',time_published:'20260925T110000',ticker_sentiment:[{ticker:'TEST',relevance_score:'0.80',ticker_sentiment_score:'0.35',ticker_sentiment_label:'Bullish'}]}
]};
const news=parseAlphaNews(alpha,'TEST',{now,lookbackHours:24});
assert.equal(news.status,'OK');assert.equal(news.direction,'LONG');assert.ok(news.score>=80);assert.equal(news.headlineCount,2);

const sec=parseSecSubmissions({filings:{recent:{form:['8-K','10-Q'],filingDate:['2026-09-25','2026-09-20'],acceptanceDateTime:['2026-09-25T10:00:00Z','2026-09-20T10:00:00Z'],accessionNumber:['1','2'],primaryDocument:['a.htm','b.htm'],items:['2.02','']}}},{now,lookbackHours:48});
assert.equal(sec.status,'OK');assert.equal(sec.filings[0].form,'8-K');assert.ok(sec.score>=90);

const setup={score:98,direction:'LONG'};
let gate=combineTechnicalAndEvent(setup,{configured:true,score:90,direction:'LONG'},{required:true,minEventScore:80});
assert.equal(gate.accepted,true);assert.ok(gate.signalScore>=95);
gate=combineTechnicalAndEvent(setup,{configured:true,score:95,direction:'SHORT'},{required:true,minEventScore:80});
assert.equal(gate.accepted,false);assert.ok(gate.reasons.some(x=>x.startsWith('EVENT_DIRECTION_MISMATCH')));
gate=combineTechnicalAndEvent(setup,{configured:true,score:70,direction:'LONG'},{required:true,minEventScore:80});
assert.equal(gate.accepted,false);assert.ok(gate.reasons.some(x=>x.startsWith('LOW_EVENT_SCORE')));
gate=combineTechnicalAndEvent({score:94,direction:'LONG'},{configured:true,score:100,direction:'LONG'},{required:true,minEventScore:80});
assert.equal(gate.accepted,false);assert.ok(gate.reasons.some(x=>x.startsWith('LOW_TECHNICAL_SCORE')));
console.log('event-smoke: OK');
