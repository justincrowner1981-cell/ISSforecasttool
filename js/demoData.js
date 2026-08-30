// Demo data is opt-in only. Production startup never loads it automatically.
window.ISS_DEMO_DATA = Array.from({length:24},(_,i)=>({hour:new Date(Date.now()+i*3600000).toISOString(),lbmp:40+i%6,gas:3.5,temperature:65,condition:"DEMO",source:"EXPLICIT DEMO"}));
