import {test,expect} from 'vitest';
import {validNumber,draftSchema,empty} from './drafts';
import {messages} from './i18n';
test('unknown differs from zero',()=>{expect(validNumber('')).toBe(false);expect(validNumber('0')).toBe(true);expect(validNumber('0',true)).toBe(false);expect(validNumber('-1')).toBe(false);expect(validNumber('Infinity')).toBe(false)});
test('draft schema rejects malformed storage',()=>{expect(draftSchema.safeParse({...empty,storage:'automatic'}).success).toBe(false)});
test('all dictionary entries have both languages',()=>{for(const value of Object.values(messages)){expect(value[0].length).toBeGreaterThan(0);expect(value[1]).toMatch(/[\u0c80-\u0cff]/)}});
