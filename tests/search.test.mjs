import test from 'node:test';import assert from 'node:assert/strict';import {searchCatalogue,searchWatchlist} from '../web/search.mjs';
test('catalogue queries require every term and respect historical classification',()=>{
 const rows=[{title:'Privacy Act',location:'-- P --',kind:'Document'},{title:'Point in Time - Privacy Act',location:'',kind:'Historical / point in time'}];
 assert.equal(searchCatalogue(rows,'PRIVACY act').length,2);assert.equal(searchCatalogue(rows,'privacy','Document').length,1);assert.equal(searchCatalogue(rows,'privacy missing').length,0);assert.equal(searchCatalogue(rows,'').length,0);
});
test('watchlist search includes each document and retains section provenance',()=>{
 const docs=['act','regulation'].map(id=>({id,title:id,official_url:'https://example.com/'+id,units:[{label:'Section 2',heading:'Consent',text:'Give access'}]}));
 const rows=searchWatchlist(docs,'consent access');assert.equal(rows.length,2);assert.equal(rows[1].document,'regulation');assert.equal(rows[0].unit.label,'Section 2');assert.equal(searchWatchlist(docs,'<img').length,0);
});
