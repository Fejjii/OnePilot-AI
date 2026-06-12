import { User, Bot } from "lucide-react";
import type { MessageResponse } from "@/types/api";
import { IntentBadge } from "./intent-badge";
import { ConfidenceBadge } from "./confidence-badge";
import { AssistantMessageContent } from "./assistant-message-content";
import { formatDateTime } from "@/lib/utils";

interface ChatMessageProps {
  message: MessageResponse;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div className="flex gap-3">
      <div
        className={
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full " +
          (isUser
            ? "bg-slate-200 text-slate-700"
            : "bg-gradient-to-br from-indigo-500 to-purple-500 text-white")
        }
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold text-slate-900">
            {isUser ? "You" : isAssistant ? "Assistant" : "System"}
          </p>
          <p className="text-[10px] text-slate-400">
            {formatDateTime(message.created_at)}
          </p>
          {isAssistant && message.intent && (
            <IntentBadge intent={message.intent} />
          )}
          {isAssistant && message.confidence > 0 && (
            <ConfidenceBadge value={message.confidence} />
          )}
        </div>
        <div
          className={
            "mt-1 rounded-lg px-3 py-2.5 text-sm leading-relaxed " +
            (isUser
              ? "whitespace-pre-wrap bg-slate-100 text-slate-900"
              : "border border-slate-200 bg-white text-slate-800 shadow-[0_1px_2px_rgba(15,23,42,0.03)]")
          }
        >
          {isAssistant ? (
            <AssistantMessageContent content={message.content} />
          ) : (
            <span className="whitespace-pre-wrap">{message.content}</span>
          )}
        </div>
      </div>
    </div>
  );
}
