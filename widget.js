;(function(){
  const me = document.currentScript;
  const url = new URL(me.src);
  const clientId = url.searchParams.get("client_id");
  if (!clientId) return console.error("Brak client_id");

  // wstawiamy przycisk
  const btn = document.createElement("button");
  btn.textContent = "💬";
  Object.assign(btn.style, {
    position: "fixed", bottom:"20px", right:"20px",
    width:"56px", height:"56px", borderRadius:"50%",
    background:"#007bff", color:"#fff", fontSize:"24px",
    border:"none", cursor:"pointer", zIndex:9999
  });
  document.body.appendChild(btn);

  // iframe z chat.html?client_id=...
  const iframe = document.createElement("iframe");
  iframe.src = `https://zawitech-frontend.onrender.com/chat.html?client_id=${clientId}`;
  Object.assign(iframe.style, {
    display:"none", position:"fixed",
    bottom:"90px", right:"20px",
    width:"420px", height:"560px",
    border:"none", borderRadius:"12px",
    boxShadow:"0 0 14px rgba(0,0,0,0.25)", zIndex:9999
  });
  document.body.appendChild(iframe);

  btn.addEventListener("click", ()=> {
    iframe.style.display = iframe.style.display === "block" ? "none" : "block";
  });
})();