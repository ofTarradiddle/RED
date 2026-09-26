'use strict';
(() => {
  window.lucide?.createIcons();
  document.querySelectorAll('.current-year').forEach(el=>el.textContent=new Date().getFullYear());
  document.querySelectorAll('.fade-in,.slide-in-left,.slide-in-right,.scale-in,.fade-in-up,.cinematic-reveal').forEach(el=>el.classList.add('visible','revealed'));
  const slides=[...document.querySelectorAll('section.slide')];
  if(slides.length){
    let current=0;
    const update=()=>{document.querySelectorAll('[data-slide-step]').forEach(b=>b.disabled=Number(b.dataset.slideStep)<0?current===0:current===slides.length-1);document.querySelectorAll('#slideProgress,#floatingProgress').forEach(el=>el.textContent=`${current+1} / ${slides.length}`);};
    const observer=new IntersectionObserver(entries=>{const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(visible){current=slides.indexOf(visible.target);update();}},{threshold:[0,.2,.5]});
    slides.forEach(slide=>observer.observe(slide));
    document.querySelectorAll('[data-slide-step]').forEach(button=>button.addEventListener('click',()=>{current=Math.max(0,Math.min(slides.length-1,current+Number(button.dataset.slideStep)));slides[current].scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});update();}));update();
  }
  document.querySelectorAll('[data-newsletter-demo]').forEach(form=>form.addEventListener('submit',event=>{event.preventDefault();if(form.reportValidity())document.querySelector('#newsletter-status').textContent='Newsletter signup is not yet connected. Your email has not been submitted or stored.';}));
  // Use one accessible mobile control for the original page-specific navigation.
  const header=document.querySelector('header') || document.querySelector('.cambria-nav');
  if(header){
    header.querySelectorAll('[data-menu-toggle],#mobile-menu-button,button.md\\:hidden').forEach(b=>b.hidden=true);
    const navigation=header.querySelector('nav') || header;
    const links=[...navigation.querySelectorAll('a[href]')].filter(a=>a.textContent.trim());
    const menu=document.createElement('nav');menu.id='restored-mobile-menu';menu.className='restored-mobile-menu';menu.setAttribute('aria-label','Mobile navigation');
    const seen=new Set();
    for(const a of links){if(seen.has(a.href))continue;seen.add(a.href);const link=document.createElement('a');link.href=a.getAttribute('href');link.append(...[...a.childNodes].map(node=>node.cloneNode(true)));menu.append(link);}
    const opportunities=document.querySelector('a[href$="/351-exchanges.html"]');
    if(opportunities&&!seen.has(opportunities.href)){const link=document.createElement('a');link.href=opportunities.getAttribute('href');link.textContent='351 Opportunities';menu.append(link);}
    const toggle=document.createElement('button');toggle.type='button';toggle.className='restored-menu-toggle';toggle.textContent='Menu';toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls',menu.id);
    const row=header.querySelector('.justify-between') || header;row.append(toggle);header.append(menu);
    const close=()=>{menu.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');};
    toggle.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));menu.classList.toggle('is-open',open);});
    menu.addEventListener('click',event=>{if(event.target.closest('a'))close();});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu.classList.contains('is-open')){close();toggle.focus();}});
  }
  document.querySelectorAll('[data-interest-fund]').forEach(card=>card.addEventListener('click',()=>{
    const form=document.querySelector('[data-interest-form]');const select=form?.querySelector('select[name=fund]');
    if(select){const option=[...select.options].find(o=>o.value===card.dataset.interestFund||o.textContent.startsWith(card.dataset.interestFund));if(option)select.value=option.value;}
    requestAnimationFrame(()=>form?.querySelector('input[name=name]')?.focus({preventScroll:true}));
  }));
  document.querySelectorAll('[data-interest-form]').forEach(form=>form.addEventListener('submit',event=>{
    event.preventDefault();if(!form.reportValidity())return;
    const get=name=>form.querySelector(`[name="${name}"]`).value.trim();
    const fund=form.querySelector('[name=fund]').selectedOptions[0].textContent;
    const type=form.querySelector('[name=type]').selectedOptions[0].textContent;
    const body=`Hello Hetzerk Asset Management,\n\nI would like to discuss a potential Section 351 contribution.\n\nName: ${get('name')}\nEmail: ${get('email')}\nInvestor type: ${type}\nFund: ${fund}\n\n${get('notes')}\n\nThis is an expression of interest, not an investment commitment.`;
    const url=`mailto:${form.dataset.recipient}?subject=${encodeURIComponent('Section 351 interest — '+fund)}&body=${encodeURIComponent(body)}`;
    location.href=url;
    const status=form.querySelector('.interest-status');status.textContent='Email draft prepared. Review the recipient and message in your email app before sending. No details have been submitted by this site.';
    const retry=document.createElement('a');retry.href=url;retry.textContent=' Open draft again';retry.className='underline';status.append(retry);
  }));
})();
