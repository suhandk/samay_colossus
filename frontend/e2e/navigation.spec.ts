import {test,expect} from '@playwright/test';
test('language selection, mobile navigation and explicit draft saving',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'English',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Welcome to SAMAY'})).toBeVisible();
 await page.getByRole('link',{name:'Plan My Sale',exact:true}).click();
 await page.getByRole('button',{name:'Continue',exact:true}).click();await expect(page.getByText('Enter a valid value before continuing.')).toBeVisible();
 await page.getByRole('button',{name:'Save draft on this device'}).click();await expect(page.getByText('Draft saved on this device.')).toBeVisible();
 await page.getByRole('link',{name:'My Plans',exact:true}).click();await expect(page.getByRole('heading',{name:'Draft — not a recommendation'})).toBeVisible();
 await page.getByRole('link',{name:'Settings',exact:true}).click();await page.getByRole('combobox').selectOption('kn');await expect(page.getByRole('heading',{name:'ಸೆಟ್ಟಿಂಗ್‌ಗಳು'})).toBeVisible();
 await page.reload();await expect(page.getByRole('heading',{name:'ಸೆಟ್ಟಿಂಗ್‌ಗಳು'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/mobile-kannada.png',fullPage:true});
});

test('guided inputs preserve unknown costs and handle unavailable recommendation',async({page})=>{
 await page.route('**/api/catalog',r=>r.fulfill({json:{crops:[{id:'test-c',names:{en:'TEST CROP',kn:'ಪರೀಕ್ಷೆ'}}],markets:[{id:'test-m',names:{en:'TEST MARKET',kn:'ಪರೀಕ್ಷೆ'}}],observed_pairs:[{crop_id:'test-c',market_id:'test-m'}],ready:false}}));
 await page.route('**/api/v1/prices/**',r=>r.fulfill({json:{items:[{variety:'v',grade:'g',modal:'1000',observation_date:'2020-01-01',freshness:'stale',source:{id:'TEST ONLY',url:'https://example.invalid'},retrieved_at:'2020-01-02T00:00:00Z'}]}}));
 await page.route('**/api/v1/recommendations',async r=>{expect(r.request().postDataJSON().transport).toBe('');await r.fulfill({status:503,json:{code:'recommendation_engine_unavailable'}})});
 await page.goto('/');await page.getByRole('button',{name:'English',exact:true}).click();await page.getByRole('link',{name:'Plan My Sale',exact:true}).click();
 await page.getByRole('button',{name:'TEST CROP'}).click();await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('button',{name:/TEST MARKET/}).click();await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('textbox',{name:'How much harvest do you have? (quintals)',exact:true}).fill('10');await page.getByRole('textbox',{name:'Compare quantities in steps of (quintals)',exact:true}).fill('1');await page.getByRole('textbox',{name:'Minimum sale lot (quintals)',exact:true}).fill('1');await page.getByRole('textbox',{name:'Buyer quantity precision (quintals)',exact:true}).fill('.01');await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('textbox').fill('2000');await page.getByRole('combobox',{name:'Variety and grade',exact:true}).selectOption('["v","g"]');await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('textbox',{name:'How much money do you need now? (₹)'}).fill('5000');await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('button',{name:'Not sure',exact:true}).click();await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.getByRole('button',{name:'Continue',exact:true}).click();await expect(page.getByRole('heading',{name:'Review your information'})).toBeVisible();
 await page.getByRole('button',{name:'Generate selling plan'}).click();await expect(page.getByText(/Selling recommendations are not available yet/)).toBeVisible();
});

test('real imported observations retain source date and stale label',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'English',exact:true}).click();
 await page.getByRole('link',{name:'Market Prices',exact:true}).last().click();
 await page.getByRole('combobox',{name:'Crop',exact:true}).selectOption('copra');await page.getByRole('combobox',{name:'Market',exact:true}).selectOption('5');
 await page.getByRole('combobox',{name:'Variety and grade',exact:true}).selectOption('["copra","local"]');
 await expect(page.getByText('Freshness: stale')).toBeVisible();await expect(page.getByRole('link',{name:/Source: bundle/})).toBeVisible();
 await page.screenshot({path:'test-results/authentic-market-mobile.png',fullPage:true});
});
