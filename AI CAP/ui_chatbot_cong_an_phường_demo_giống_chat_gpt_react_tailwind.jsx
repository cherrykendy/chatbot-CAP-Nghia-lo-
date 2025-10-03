import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * Demo UI: Chatbot Công An Phường — phong cách ChatGPT
 * - React single-file component (có thể nhúng vào Vite/Next)
 * - TailwindCSS classes cho giao diện sạch, hiện đại
 * - Có quick replies, typing indicator, upload nút, và placeholder API
 */

const QUICK_REPLIES = [
  { label: "📌 Đăng ký thường trú", text: "Đăng ký thường trú" },
  { label: "🛏️ Đăng ký tạm trú", text: "Đăng ký tạm trú" },
  { label: "🧾 Lệ phí/miễn lệ phí", text: "Lệ phí thủ tục" },
  { label: "📄 Hồ sơ cần nộp", text: "Hồ sơ cần nộp" },
  { label: "🔎 Tra cứu hồ sơ", text: "Tra cứu tình trạng hồ sơ" },
];

const BOT_AVATAR = (
  <div className="h-8 w-8 rounded-full grid place-items-center bg-emerald-600 text-white font-semibold shadow">
    CA
  </div>
);

const USER_AVATAR = (
  <div className="h-8 w-8 rounded-full grid place-items-center bg-sky-600 text-white font-semibold shadow">
    U
  </div>
);

function Message({ role, content, time }) {
  const isUser = role === "user";
  return (
    <div className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && BOT_AVATAR}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm text-sm leading-relaxed whitespace-pre-wrap ${
          isUser ? "bg-sky-50 border border-sky-100" : "bg-white border border-zinc-100"
        }`}
      >
        <div className="text-[13px] text-zinc-400 mb-1">{isUser ? "Bạn" : "Chatbot Công an phường"} · {time}</div>
        <div className="text-zinc-800">{content}</div>
      </div>
      {isUser && USER_AVATAR}
    </div>
  );
}

function TypingBubble() {
  return (
    <div className="flex items-center gap-2 text-zinc-500">
      {BOT_AVATAR}
      <div className="flex items-center gap-1 bg-white border border-zinc-100 rounded-2xl px-3 py-2 shadow-sm">
        <span className="w-2 h-2 rounded-full bg-zinc-300 animate-bounce" style={{animationDelay: "0ms"}} />
        <span className="w-2 h-2 rounded-full bg-zinc-300 animate-bounce" style={{animationDelay: "150ms"}} />
        <span className="w-2 h-2 rounded-full bg-zinc-300 animate-bounce" style={{animationDelay: "300ms"}} />
      </div>
    </div>
  );
}

export default function ChatCAP() {
  const [messages, setMessages] = useState([
    {
      id: "m1",
      role: "assistant",
      content:
        "Xin chào! Tôi là trợ lý 24/7 của Công an phường. Bạn cần hỗ trợ về thường trú, tạm trú, tra cứu hồ sơ hay phí/lệ phí?",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    // Auto scroll to bottom on new message
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const nowStr = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const fakeBotAnswer = async (text) => {
    // Placeholder: mô phỏng gọi API backend của bạn
    // Ở sản phẩm thật, bạn sẽ gọi /api/chat và stream kết quả
    await new Promise((r) => setTimeout(r, 700));

    // Routing sơ bộ theo intent
    const t = text.toLowerCase();
    if (t.includes("thường trú")) {
      return (
        "🔎 Giải thích nhanh:\n- Thường trú: nơi ở ổn định lâu dài.\n- Tạm trú: nơi ở hiện tại từ 30 ngày trở lên.\n\n📝 Nếu bạn muốn *đăng ký thường trú*, vui lòng cho tôi biết: đã có VNeID mức 2 chưa, địa chỉ đăng ký, và mối quan hệ với chủ hộ."
      );
    }
    if (t.includes("tạm trú")) {
      return (
        "🛏️ Đăng ký tạm trú online qua VNeID:\n1) Mở VNeID → Thủ tục hành chính → Đăng ký tạm trú.\n2) Xác thực passcode/Face/TouchID.\n3) Tạo mới yêu cầu, điền địa chỉ, thời hạn tạm trú, đính kèm hợp đồng thuê (ký trong 30 ngày gần nhất).\n\nBạn muốn tôi mở form hỏi đáp để thu thập thông tin và tạo checklist hồ sơ không?"
      );
    }
    if (t.includes("lệ phí") || t.includes("phí")) {
      return (
        "💵 Lệ phí: tùy địa phương, nhiều trường hợp được miễn/giảm (trẻ em, người có công…).\nBạn cho tôi biết thủ tục cụ thể để tôi báo lệ phí tương ứng nhé."
      );
    }
    if (t.includes("hồ sơ")) {
      return (
        "📄 Hồ sơ cơ bản gồm: tờ khai, giấy tờ chỗ ở hợp pháp (ví dụ hợp đồng thuê, giấy tờ nhà), giấy tờ nhân thân.\nTôi có thể tạo checklist cá nhân hoá nếu bạn cung cấp vài thông tin."
      );
    }
    if (t.includes("tra cứu")) {
      return (
        "🔍 Bạn có mã hồ sơ/CMND/CCCD liên quan không? Tôi sẽ hướng dẫn tra cứu tình trạng xử lý và cách nhận kết quả điện tử."
      );
    }
    return (
      "Tôi đã nhận được câu hỏi. Bạn có thể nói rõ thủ tục (thường trú/tạm trú/khác) để tôi hướng dẫn chi tiết theo kịch bản mới nhất."
    );
  };

  const sendMessage = async (text) => {
    if (!text.trim()) return;
    const userMsg = { id: crypto.randomUUID(), role: "user", content: text.trim(), time: nowStr() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const reply = await fakeBotAnswer(text);
      const botMsg = { id: crypto.randomUUID(), role: "assistant", content: reply, time: nowStr() };
      setMessages((m) => [...m, botMsg]);
    } finally {
      setLoading(false);
    }
  };

  const onQuickReply = (q) => sendMessage(q.text);

  const onUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadName(file.name);
      // Thực tế: tải file lên server của bạn tại đây
    }
  };

  const Header = useMemo(
    () => (
      <header className="sticky top-0 z-10 backdrop-blur supports-[backdrop-filter]:bg-white/70 bg-white/90 border-b border-zinc-200">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl grid place-items-center bg-emerald-600 text-white font-semibold shadow-sm">CA</div>
            <div>
              <div className="font-semibold">Trợ lý Công an phường</div>
              <div className="text-xs text-zinc-500">Giao diện mẫu · giống phong cách ChatGPT</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <span className="hidden sm:inline">Bảo mật • 24/7 • Vietnameses UI</span>
          </div>
        </div>
      </header>
    ),
    []
  );

  return (
    <div className="h-screen w-full bg-zinc-50 text-zinc-900 flex flex-col">
      {Header}

      {/* Quick replies */}
      <div className="max-w-4xl mx-auto w-full px-4 pt-3">
        <div className="flex gap-2 overflow-x-auto pb-3 hide-scrollbar">
          {QUICK_REPLIES.map((q) => (
            <button
              key={q.label}
              onClick={() => onQuickReply(q)}
              className="shrink-0 rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm hover:bg-zinc-50 active:scale-[.98]"
            >
              {q.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat body */}
      <main ref={scrollRef} className="max-w-4xl mx-auto w-full px-4 flex-1 overflow-y-auto py-4 space-y-4">
        {messages.map((m) => (
          <Message key={m.id} role={m.role} content={m.content} time={m.time} />
        ))}
        {loading && <TypingBubble />}
      </main>

      {/* Composer */}
      <div className="border-t border-zinc-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="max-w-3xl mx-auto w-full px-3 py-3">
          <div className="rounded-2xl border border-zinc-200 bg-white shadow-sm p-2">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(input);
                  }
                }}
                placeholder="Nhập câu hỏi… (Ví dụ: Hướng dẫn đăng ký tạm trú trên VNeID)"
                rows={1}
                className="flex-1 resize-none bg-transparent outline-none p-2 text-[15px] leading-6 max-h-40"
              />
              <div className="flex items-center gap-1">
                <label className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 px-2 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50 cursor-pointer">
                  <input type="file" className="hidden" onChange={onUpload} />
                  📎 Tệp
                </label>
                <button
                  onClick={() => sendMessage(input)}
                  className="rounded-xl bg-emerald-600 text-white px-3 py-2 text-sm font-medium hover:bg-emerald-700 active:scale-[.98]"
                >
                  Gửi
                </button>
              </div>
            </div>
            {uploadName && (
              <div className="text-xs text-zinc-500 px-2 pt-1">Đã chọn tệp: {uploadName}</div>
            )}
            <div className="text-[11px] text-zinc-400 px-2 pt-1">Mẹo: Nhấn Enter để gửi, Shift+Enter để xuống dòng.</div>
          </div>
        </div>
      </div>

      {/* Styles bổ sung */}
      <style>{`
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
}
