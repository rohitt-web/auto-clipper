const urlInput=document.querySelector('#vod-url');
const language=document.querySelector('#language');
const analyseButton=document.querySelector('#analyse');
const renderButton=document.querySelector('#render');
const statusBox=document.querySelector('#status');
const momentsSection=document.querySelector('#moments');
const momentList=document.querySelector('#moment-list');
const count=document.querySelector('#count');
const downloads=document.querySelector('#downloads');
const downloadList=document.querySelector('#download-list');
let activeJob=null;
let pollHandle=null;
async function readApiResponse(response){
  const raw=await response.text();
  let data;
  try{data=raw?JSON.parse(raw):{};}
  catch{
    const preview=raw.replace(/\\s+/g,' ').slice(0,300);
    throw new Error('Server returned a non-JSON response (HTTP '+response.status+'): '+(preview||'empty response'));
  }
  if(!response.ok)throw new Error(data.detail||data.message||('Request failed (HTTP '+response.status+').'));
  return data;
}
function showStatus(message){statusBox.hidden=false;statusBox.textContent=message;}
function validSource(value){try{const u=new URL(value);const h=u.hostname.toLowerCase();return u.protocol==='https:'&&(h==='twitch.tv'||h.endsWith('.twitch.tv')||h==='kick.com'||h.endsWith('.kick.com')||h==='youtube.com'||h.endsWith('.youtube.com')||h==='youtu.be');}catch{return false;}}
function timeLabel(seconds){const s=Math.floor(seconds||0);return Math.floor(s/3600)+':'+String(Math.floor(s%3600/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function renderMoments(items){
  momentList.replaceChildren();
  items.forEach((m,i)=>{
    const card=document.createElement('article');card.className='moment';
    const top=document.createElement('div');top.className='moment-top';
    const check=document.createElement('input');check.type='checkbox';check.className='moment-check';check.value=String(i);check.setAttribute('aria-label','Select moment '+(i+1));
    const title=document.createElement('strong');title.textContent=m.title||('Moment '+(i+1));
    top.append(check,title);
    const desc=document.createElement('p');desc.textContent=timeLabel(m.start_seconds)+' – '+timeLabel(m.end_seconds)+' · Score '+m.score;
    const excerpt=document.createElement('p');excerpt.className='excerpt';excerpt.textContent=m.excerpt||'No transcript excerpt available.';
    card.append(top,desc,excerpt);momentList.append(card);
  });
  count.textContent=items.length+' found';momentsSection.hidden=items.length===0;
}
async function pollJob(){
  if(!activeJob)return;
  try{
    const response=await fetch('/api/jobs/'+activeJob);const data=await readApiResponse(response);
    showStatus(data.message+' ('+data.progress+'%)');
    if(data.status==='ready'){
      clearInterval(pollHandle);pollHandle=null;renderMoments(data.moments||[]);
      if(!data.moments?.length)showStatus('Transcription completed, but no candidate moments were detected. Try another VOD or language setting.');
      analyseButton.disabled=false;
    }else if(data.status==='complete'){
      clearInterval(pollHandle);pollHandle=null;analyseButton.disabled=false;renderButton.disabled=false;downloadList.replaceChildren();
      (data.clips||[]).forEach(clip=>{const link=document.createElement('a');link.href=clip.url;link.textContent='Download clip '+(clip.index+1);link.className='download-link';link.download=clip.filename;downloadList.append(link);});
      downloads.hidden=false;showStatus(data.message);
    }else if(data.status==='failed'){
      clearInterval(pollHandle);pollHandle=null;analyseButton.disabled=false;renderButton.disabled=false;
      showStatus(data.message+': '+(data.error||'Unknown error'));
    }
  }catch(error){clearInterval(pollHandle);pollHandle=null;analyseButton.disabled=false;renderButton.disabled=false;showStatus(error.message);}
}
analyseButton.addEventListener('click',async()=>{
  const vodUrl=urlInput.value.trim();if(!validSource(vodUrl)){showStatus('Enter an HTTPS public YouTube, Twitch, or Kick VOD URL.');return;}
  analyseButton.disabled=true;momentsSection.hidden=true;downloads.hidden=true;activeJob=null;showStatus('Submitting VOD…');
  try{
    const response=await fetch('/api/analyse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:vodUrl,caption_language:language.value})});
    const data=await readApiResponse(response);
    activeJob=data.job_id;showStatus('VOD queued. Keep this page open while it is analysed.');
    pollHandle=setInterval(pollJob,2500);await pollJob();
  }catch(error){analyseButton.disabled=false;showStatus(error.message||'Could not reach the analysis server.');}
});
renderButton.addEventListener('click',async()=>{
  if(!activeJob)return;const selected=[...document.querySelectorAll('.moment-check:checked')].map(el=>Number(el.value));
  if(!selected.length){showStatus('Select at least one moment first.');return;}
  renderButton.disabled=true;showStatus('Starting clip rendering…');
  try{
    const response=await fetch('/api/jobs/'+activeJob+'/clips',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({moment_indices:selected})});
    const data=await readApiResponse(response);
    showStatus(data.message);pollHandle=setInterval(pollJob,2500);
  }catch(error){renderButton.disabled=false;showStatus(error.message);}
});
