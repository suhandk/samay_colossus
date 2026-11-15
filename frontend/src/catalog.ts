import {z} from 'zod';
const entry=z.object({id:z.string(),names:z.object({en:z.string(),kn:z.string()})});
export const catalogSchema=z.object({crops:z.array(entry),markets:z.array(entry),observed_pairs:z.array(z.object({crop_id:z.string(),market_id:z.string()})),ready:z.boolean()});
