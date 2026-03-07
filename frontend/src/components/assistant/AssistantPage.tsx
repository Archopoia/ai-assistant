import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { assistantAPI } from '../../services/api';
import type {
  AssistantChartPayload,
  AssistantConversationSummary,
  AssistantMessage,
  AssistantResponseMode,
} from '../../types';

const PIE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444'];

const renderInline = (text: string): React.ReactNode => {
  // Some model responses return escaped markdown like \*\*bold\*\*.
  const normalized = text.replace(/\\\*/g, '*');
  const parts = normalized.split(/(\*\*.+?\*\*)/g);
  return parts.map((part, idx) => {
    const boldMatch = part.match(/^\*\*(.+?)\*\*$/);
    if (boldMatch) {
      return (
        <strong key={`b-${idx}`} className="font-semibold">
          {boldMatch[1]}
        </strong>
      );
    }
    return <React.Fragment key={`t-${idx}`}>{part}</React.Fragment>;
  });
};

const renderSimpleMarkdown = (content: string): React.ReactNode => {
  return content.split('\n').map((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('### ')) {
      return (
        <h4 key={`h-${idx}`} className="font-semibold text-gray-900 mt-2 mb-1">
          {renderInline(trimmed.replace('### ', ''))}
        </h4>
      );
    }
    if (trimmed.startsWith('- ')) {
      return (
        <li key={`li-${idx}`} className="ml-5 list-disc text-gray-700">
          {renderInline(trimmed.slice(2))}
        </li>
      );
    }
    if (trimmed.startsWith('• ')) {
      return (
        <li key={`bli-${idx}`} className="ml-5 list-disc text-gray-700">
          {renderInline(trimmed.slice(2))}
        </li>
      );
    }
    return (
      <p key={`p-${idx}`} className="text-gray-700 whitespace-pre-wrap">
        {renderInline(line)}
      </p>
    );
  });
};

const ChartPreview: React.FC<{ chart: AssistantChartPayload }> = ({ chart }) => {
  if (!chart.data?.length) return null;
  const xKey = chart.x_key || Object.keys(chart.data[0])[0];
  const yKeys = chart.y_keys?.length ? chart.y_keys : Object.keys(chart.data[0]).filter((k) => k !== xKey);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mt-2">
      <h5 className="font-semibold text-gray-900">{chart.title}</h5>
      {chart.description && <p className="text-sm text-gray-600 mb-3">{chart.description}</p>}
      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          {chart.chart_type === 'line' ? (
            <LineChart data={chart.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {yKeys.map((key, index) => (
                <Line key={key} type="monotone" dataKey={key} stroke={PIE_COLORS[index % PIE_COLORS.length]} strokeWidth={2} />
              ))}
            </LineChart>
          ) : chart.chart_type === 'bar' ? (
            <BarChart data={chart.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {yKeys.map((key, index) => (
                <Bar key={key} dataKey={key} fill={PIE_COLORS[index % PIE_COLORS.length]} />
              ))}
            </BarChart>
          ) : (
            <PieChart>
              <Pie data={chart.data} dataKey={yKeys[0]} nameKey={xKey} outerRadius={100} label>
                {chart.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export const AssistantPage: React.FC = () => {
  const [conversation, setConversation] = useState<AssistantConversationSummary | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [responseMode, setResponseMode] = useState<AssistantResponseMode>('concise');
  const [latestChart, setLatestChart] = useState<AssistantChartPayload | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      setPageError(null);
      try {
        let convo = await assistantAPI.getLatestConversation();
        if (!convo) {
          convo = await assistantAPI.createConversation('Wellness Assistant Chat', responseMode);
        }
        setConversation(convo);
        setResponseMode(convo.response_mode);
        const detail = await assistantAPI.getConversation(convo.id);
        setMessages(detail.messages);
      } catch (error) {
        console.error(error);
        setPageError('Failed to load assistant history.');
      }
    };
    init();
  }, []);

  const canSend = useMemo(() => inputValue.trim().length > 0 && inputValue.length <= 6000 && !loading && !!conversation, [inputValue, loading, conversation]);

  const onSend = async () => {
    const cleaned = inputValue.trim();
    if (!cleaned) {
      setPageError('Please type a message before sending.');
      return;
    }
    if (cleaned.length > 6000) {
      setPageError('Message is too long. Keep it under 6000 characters.');
      return;
    }
    if (!conversation) return;

    setLoading(true);
    setPageError(null);
    setInputValue('');
    try {
      const response = await assistantAPI.sendMessage(conversation.id, cleaned, responseMode);
      setConversation(response.conversation);
      setMessages((prev) => [...prev, response.user_message, response.assistant_message]);
      setLatestChart(response.chart || null);
      setSuggestion(response.suggested_visualization || null);
    } catch (error: any) {
      console.error(error);
      setPageError(error?.response?.data?.detail || 'Assistant request failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      <div className="bg-white shadow-md rounded-lg p-6">
        <div className="flex justify-between items-center mb-4 gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Wellness Assistant</h2>
            <p className="text-sm text-gray-600">Ask about health metrics, meal plans, recipes, nutrition, and charts.</p>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="response-mode" className="text-sm text-gray-700">
              Response mode
            </label>
            <select
              id="response-mode"
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
              value={responseMode}
              onChange={(event) => setResponseMode(event.target.value as AssistantResponseMode)}
            >
              <option value="concise">Concise</option>
              <option value="detailed">Detailed</option>
            </select>
          </div>
        </div>

        {pageError && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">{pageError}</div>}

        <div className="border border-gray-200 rounded-lg p-4 h-[460px] overflow-y-auto bg-gray-50">
          {messages.length === 0 ? (
            <p className="text-gray-600 text-sm">
              Start with something like: &quot;What&apos;s my current BMI?&quot; or &quot;Show me my protein intake chart this week.&quot;
            </p>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                <div
                  className={`inline-block max-w-[80%] rounded-lg px-4 py-3 ${
                    msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200'
                  }`}
                >
                  <div className="text-xs mb-1 opacity-80">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                  {msg.role === 'user' ? <p className="whitespace-pre-wrap">{msg.content}</p> : <div>{renderSimpleMarkdown(msg.content)}</div>}
                  {msg.role === 'assistant' && msg.metadata_json?.chart_payload && (
                    <ChartPreview chart={msg.metadata_json.chart_payload as AssistantChartPayload} />
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {latestChart && (
          <div className="mt-4">
            <ChartPreview chart={latestChart} />
          </div>
        )}
        {suggestion && <div className="mt-3 text-sm text-blue-800 bg-blue-50 border border-blue-100 rounded p-2">{suggestion}</div>}

        <div className="mt-4 flex gap-2">
          <textarea
            className="flex-1 border border-gray-300 rounded-lg p-3 text-sm min-h-[84px] focus:ring-2 focus:ring-blue-300 focus:outline-none"
            placeholder="Ask a follow-up question..."
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
          />
          <button
            className={`px-4 py-2 rounded-lg text-white text-sm self-end ${canSend ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-400 cursor-not-allowed'}`}
            onClick={onSend}
            disabled={!canSend}
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Safety note: This assistant is not a medical diagnosis tool. For urgent symptoms, seek professional care.
        </p>
      </div>
    </div>
  );
};
