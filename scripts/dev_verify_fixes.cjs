/** Verify audit fixes: clients carry project_id (CRITICAL #1), workflow/roadmap
 * resolves with the real project_id (HIGH #3). */
const crypto = require("crypto");
const { chromium } = require("playwright");
const BASE = "http://localhost:3000";
const TOTP_SECRET = process.env.MARCOS_TOTP_SECRET || "";
function b32(s){const a="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";let b="";for(const c of s.toUpperCase())if(a.indexOf(c)>=0)b+=a.indexOf(c).toString(2).padStart(5,"0");const o=[];for(let i=0;i+8<=b.length;i+=8)o.push(parseInt(b.slice(i,i+8),2));return Buffer.from(o);}
function totp(s){const k=b32(s);const buf=Buffer.alloc(8);buf.writeBigUInt64BE(BigInt(Math.floor(Date.now()/1000/30)));const h=crypto.createHmac("sha1",k).update(buf).digest();const o=h[h.length-1]&0xf;return((((h[o]&0x7f)<<24)|((h[o+1]&0xff)<<16)|((h[o+2]&0xff)<<8)|(h[o+3]&0xff))%1000000).toString().padStart(6,"0");}
(async()=>{
  const b=await chromium.launch();const ctx=await b.newContext();
  await ctx.addInitScript(()=>{try{localStorage.setItem("fulkro_admin_tour_completed","true");}catch{}});
  const p=await ctx.newPage();
  await p.goto(`${BASE}/login`,{waitUntil:"networkidle"});await p.waitForSelector("#email");
  await p.fill("#email",process.env.MARCOS_EMAIL||"marcosmata@fulkro.es");await p.fill("#password",process.env.MARCOS_PASSWORD||"");
  await p.getByRole("button",{name:"Acceder"}).click();
  await p.waitForSelector('input[placeholder="000000"]',{timeout:20000});
  for(let i=0;i<2;i++){await p.fill('input[placeholder="000000"]',totp(TOTP_SECRET));await p.getByRole("button",{name:"Validar código"}).click();try{await p.waitForURL(u=>!u.pathname.endsWith("/login"),{timeout:12000});break;}catch{await p.fill('input[placeholder="000000"]',"");}}
  const get=(path)=>p.evaluate(async(x)=>{const r=await fetch(x,{credentials:"include",headers:{Accept:"application/json"}});const t=await r.text();return{s:r.status,t};},path);
  const cl=await get("/api/v1/clients");
  let clients=[];try{clients=JSON.parse(cl.t);}catch{}
  const withPid=clients.filter(c=>c.project_id);
  console.log(`CRITICAL #1 · /clients=${cl.s} · total=${clients.length} · con project_id=${withPid.length}`);
  if(withPid.length){
    const pid=withPid[0].project_id;
    const hdr=await get(`/api/v1/projects/${pid}/header`);
    const rm=await get(`/api/v1/workflow/roadmap/${pid}`);
    const cp=await get(`/api/v1/workflow/current-phase/${pid}`);
    console.log(`   project_id=${pid.slice(0,8)} · header=${hdr.s} · HIGH#3 roadmap=${rm.s} · current-phase=${cp.s}`);
  } else { console.log("   (ningún cliente con project_id · crea uno primero)"); }
  await b.close();
})();
