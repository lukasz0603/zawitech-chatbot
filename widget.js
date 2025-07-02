;(function(){
  const me = document.currentScript;
  const url = new URL(me.src);
  const clientId = url.searchParams.get("client_id");
  if (!clientId) {
    console.error("Brak client_id");
    return;
  }

  // kontener dla labelki i przycisku
  const container = document.createElement("div");
  container.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    text-align: center;
  `;

  // napis „AI Asystent”
  const label = document.createElement("div");
  label.textContent = "AI Asystent";
  label.style.cssText = `
    color: #333;
    font-size: 0.9rem;
    margin-bottom: 4px;
    font-weight: bold;
  `;
  container.appendChild(label);

  // przycisk chatu
  const btn = document.createElement("button");
  btn.textContent = "💬";
  Object.assign(btn.style, {
    borderRadius: "50%",
    backgroundColor: "#007bff",
    color: "#fff",
    padding: "18px",
    border: "none",
    fontSize: "24px",
    cursor: "pointer",
    boxShadow: "0 4px 8px rgba(0,0,0,0.2)",
    transition: "transform 0.2s, box-shadow 0.2s"
  });
  btn.onmouseover = () => {
    btn.style.boxShadow = "0 6px 12px rgba(0,0,0,0.3)";
    btn.style.transform = "scale(1.05)";
  };
  btn.onmouseout = () => {
    btn.style.boxShadow = "0 4px 8px rgba(0,0,0,0.2)";
    btn.style.transform = "scale(1)";
  };
  container.appendChild(btn);

  document.body.appendChild(container);

  // iframe z chatem
  const iframe = document.createElement("iframe");
  iframe.id = "chatbot-frame";
  iframe.src = `https://zawitech-frontend.onrender.com/chat.html?client_id=${clientId}`;
  Object.assign(iframe.style, {
    display: "none",
    position: "fixed",
    bottom: "90px",
    right: "20px",
    width: "420px",
    height: "560px",
    border: "none",
    borderRadius: "12px",
    boxShadow: "0 0 14px rgba(0,0,0,0.25)",
    zIndex: 9999
  });
  document.body.appendChild(iframe);

  btn.addEventListener("click", () => {
    iframe.style.display = iframe.style.display === "block" ? "none" : "block";
  });
})();
