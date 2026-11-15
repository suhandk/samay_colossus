import {test,expect} from 'vitest';
import {catalogSchema} from './catalog';
test('accepts empty unavailable catalog',()=>{expect(catalogSchema.parse({crops:[],markets:[],observed_pairs:[],ready:false}).ready).toBe(false)});
test('rejects malformed API response',()=>{expect(()=>catalogSchema.parse({crops:[{id:'test'}]})).toThrow()});
