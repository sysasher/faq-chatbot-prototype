import { useEffect, useRef, useState } from "react";
import { MessageCircle, RotateCcw, Send } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const WELCOME_MESSAGE = {
  role: "bot",
  text: "Hi! I'm the FAQ assistant. Ask me a question and I'll answer it using our FAQ content.",
};

function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/api/faqs`)
      .then((res) => res.json())
      .then((data) => setSuggestions((data.faqs || []).slice(0, 4)))
      .catch(() => setSuggestions([]));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function sendMessage(text) {
    const question = text.trim();
    if (!question || isSending) return;

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setIsSending(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });

      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "bot", text: data.answer }]);
    } catch {
      setError("Could not reach the chatbot backend. Is the FastAPI server running?");
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage(input);
  }

  function handleClear() {
    setMessages([WELCOME_MESSAGE]);
    setError("");
  }

  return (
    <div className="page">
      <div className="chat-card">
        <header className="chat-header">
          <div className="chat-header-title">
            <MessageCircle size={20} />
            <span>FAQ Assistant</span>
          </div>
          <button type="button" className="icon-button" onClick={handleClear} title="Clear chat">
            <RotateCcw size={16} />
          </button>
        </header>

        <div className="chat-messages">
          {messages.map((message, index) => (
            <div key={index} className={`bubble-row ${message.role}`}>
              <div className={`bubble ${message.role}`}>{message.text}</div>
            </div>
          ))}

          {isSending && (
            <div className="bubble-row bot">
              <div className="bubble bot typing">Thinking…</div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {suggestions.length > 0 && messages.length <= 1 && (
          <div className="suggestions">
            {suggestions.map((question) => (
              <button
                key={question}
                type="button"
                className="suggestion-chip"
                onClick={() => sendMessage(question)}
              >
                {question}
              </button>
            ))}
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        <form className="chat-input-row" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask a question…"
            disabled={isSending}
          />
          <button type="submit" disabled={isSending || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
