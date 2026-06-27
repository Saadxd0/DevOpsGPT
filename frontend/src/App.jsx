import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Terminal, Send, Cpu, Database, FileText, Loader2, Sparkles, ShieldCheck, Activity, Bot, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './App.css';

const samplePrompts = [
  'Summarize the current infrastructure risks',
  'Help me debug a Docker container issue',
  'Explain the deployment pipeline and bottlenecks'
];

export default function App() {
  const [messages, setMessages] = useState([
    { role: 'model', content: 'System online. I am DevOpsGPT. Ask me anything about your infrastructure, containers, deployments, or docs.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input.trim();
    setInput('');

    // Immediately append the user's message locally so the UI shows it
    const updatedMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(updatedMessages);
    setLoading(true);

    try {
      // Build history for the backend: exclude the initial system greeting (index 0)
      // and exclude the newest user message we just appended (last element).
      const historyForBackend = updatedMessages.slice(1, -1).map(m => ({ role: m.role, content: m.content }));

      const response = await axios.post('http://127.0.0.1:8000/api/v1/chat', {
        history: historyForBackend,
        message: userMsg
      });

      setMessages(prev => [...prev, { role: 'model', content: response.data.response }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'model', content: '**Error:** Failed to connect to the backend. Is Uvicorn running?' }]);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt) => {
    setInput(prompt);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <div className="brand-icon">
            <Terminal size={24} />
          </div>
          <div>
            <p className="eyebrow">AI Operations Copilot</p>
            <h1>DevOpsGPT</h1>
          </div>
        </div>

        <div className="status-pill">
          <ShieldCheck size={16} />
          Secure & online
        </div>

        <div className="sidebar-card">
          <div className="sidebar-card__title">What it can assist with</div>
          <ul>
            <li><Cpu size={16} /> Infrastructure analysis</li>
            <li><Database size={16} /> Docker and services</li>
            <li><FileText size={16} /> Documentation and troubleshooting</li>
          </ul>
        </div>

        <div className="sidebar-card">
          <div className="sidebar-card__title">Try a prompt</div>
          <div className="prompt-list">
            {samplePrompts.map((prompt) => (
              <button key={prompt} type="button" onClick={() => handlePromptClick(prompt)} aria-label={`Try prompt: ${prompt}`}>
                <span>{prompt}</span>
                <ChevronRight size={14} />
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Live assistant</p>
            <h2>Operational intelligence at your fingertips</h2>
          </div>
          <div className="topbar-badges">
            <span className="badge"><Activity size={14} /> Real time</span>
            <span className="badge"><Bot size={14} /> Smart agent</span>
          </div>
        </header>

        <div className="hero-card">
          <div className="hero-copy">
            <div className="hero-badge">
              <Sparkles size={16} />
              Run smarter incident workflows
            </div>
            <h3>Inspect your stack, troubleshoot faster, and get clear operational guidance.</h3>
            <p>DevOpsGPT turns complex infrastructure questions into concise, actionable answers.</p>
          </div>
          <div className="hero-stats">
            <div>
              <strong>24/7</strong>
              <span>Monitoring insight</span>
            </div>
            <div>
              <strong>3x</strong>
              <span>Faster triage</span>
            </div>
            <div>
              <strong>100%</strong>
              <span>Context aware</span>
            </div>
          </div>
        </div>

        <div className="chat-card">
          <div className="chat-body">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message-row ${msg.role === 'user' ? 'user' : 'model'}`}>
                <div className={`message-bubble ${msg.role === 'user' ? 'user' : 'model'}`}>
                  {msg.role === 'model' ? (
                    <div className="markdown">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message-row model">
                <div className="message-bubble model typing">
                  <Loader2 className="spin" size={18} />
                  <span>Agent is analyzing your infrastructure...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="composer" onSubmit={handleSend}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              placeholder="Ask about CPU, Docker, Git, or documentation..."
            />
            <button type="submit" disabled={loading || !input.trim()}>
              <Send size={18} />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
