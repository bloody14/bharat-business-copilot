"use client";

import { useState, useRef, useEffect } from "react";
import { useCopilot } from "@/hooks/use-copilot";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Bot, User, Send, Mic, MicOff } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import { ActionProposal } from "@/hooks/use-copilot";
import { useSpeech, SpeechLang } from "@/hooks/use-speech";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function CopilotActionCard({ proposal }: { proposal: ActionProposal }) {
  const { executeAction, cancelAction } = useCopilot();
  const [status, setStatus] = useState(proposal.status);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      await executeAction(proposal.action_id);
      setStatus("executed");
      toast.success("Action executed successfully.");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to execute action.");
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCancel = async () => {
    setIsExecuting(true);
    try {
      await cancelAction(proposal.action_id);
      setStatus("cancelled");
      toast.info("Action cancelled.");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to cancel action.");
    } finally {
      setIsExecuting(false);
    }
  };

  if (status === "executed") {
    return (
      <div className="bg-teal-900/30 border border-teal-800/50 rounded-lg p-4">
        <p className="text-teal-400 font-medium text-sm mb-1">{proposal.display_title}</p>
        <p className="text-teal-200/70 text-xs">Successfully executed.</p>
      </div>
    );
  }

  if (status === "cancelled") {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 opacity-50">
        <p className="text-slate-400 font-medium text-sm mb-1">{proposal.display_title}</p>
        <p className="text-slate-500 text-xs">Cancelled.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 shadow-lg">
      <div className="mb-3">
        <h4 className="font-semibold text-slate-100">{proposal.display_title}</h4>
        <p className="text-slate-400 text-xs mt-1">{proposal.display_subtitle}</p>
      </div>
      <div className="flex justify-between items-end">
        <div className="text-lg font-bold text-teal-400">
          {proposal.display_quantity}
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="border-slate-600 text-slate-300 hover:bg-slate-700 h-8"
            onClick={handleCancel}
            disabled={isExecuting}
          >
            Cancel
          </Button>
          <Button 
            size="sm" 
            className="bg-teal-600 hover:bg-teal-700 text-white h-8"
            onClick={handleExecute}
            disabled={isExecuting}
          >
            {isExecuting ? "Confirming..." : "Confirm"}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface CopilotSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CopilotSheet({ open, onOpenChange }: CopilotSheetProps) {
  const [input, setInput] = useState("");
  const [speechLang, setSpeechLang] = useState<SpeechLang>("hi-IN");
  const { messages, isLoading, error, sendMessage } = useCopilot();
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const { isSupported, isListening, startListening, stopListening } = useSpeech({
    lang: speechLang,
    onTranscriptChange: (text) => setInput(text)
  });

  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  };

  const handleSuggestion = (suggestion: string) => {
    sendMessage(suggestion);
  };

  const SUGGESTIONS = [
    "Which products should I reorder?",
    "Show my out-of-stock products",
    "Summarize my inventory",
    "What changed in my stock recently?"
  ];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      
      <SheetContent className="w-full sm:max-w-md flex flex-col h-full bg-slate-900 border-slate-800 p-0 text-slate-100">
        <SheetHeader className="p-4 border-b border-slate-800 bg-slate-900/95 sticky top-0 z-10 flex flex-row items-center justify-between">
          <SheetTitle className="flex items-center gap-2 text-slate-100">
            <Bot className="h-5 w-5 text-teal-400" />
            Bharat Business Copilot
          </SheetTitle>
          {isSupported && (
            <Select value={speechLang} onValueChange={(val: SpeechLang) => setSpeechLang(val)}>
              <SelectTrigger className="w-24 h-8 text-xs bg-slate-800 border-slate-700 text-slate-300">
                <SelectValue placeholder="Lang" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hi-IN" className="text-xs">Hindi/Hinglish</SelectItem>
                <SelectItem value="en-IN" className="text-xs">English</SelectItem>
              </SelectContent>
            </Select>
          )}
        </SheetHeader>

        <ScrollArea className="flex-1 p-4">
          <div className="flex flex-col gap-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-6 pt-10">
                <div className="bg-slate-800 p-4 rounded-full">
                  <Bot className="h-10 w-10 text-teal-400" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-medium text-slate-200">Hi, I&apos;m your Copilot</h3>
                  <p className="text-sm text-slate-400">
                    I can help you analyze your inventory and track stock movements. What would you like to know?
                  </p>
                </div>
                
                <div className="flex flex-col gap-2 w-full max-w-sm">
                  {SUGGESTIONS.map((s) => (
                    <Button 
                      key={s} 
                      variant="outline" 
                      className="justify-start text-left bg-slate-800/50 border-slate-700 hover:bg-slate-800 hover:text-slate-200 h-auto py-3 whitespace-normal"
                      onClick={() => handleSuggestion(s)}
                    >
                      {s}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex items-start gap-3 ${
                    m.role === "user" ? "flex-row-reverse" : "flex-row"
                  }`}
                >
                  <div className={`flex-shrink-0 p-2 rounded-full ${m.role === "user" ? "bg-slate-700" : "bg-teal-900/50"}`}>
                    {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-teal-400" />}
                  </div>
                  <div
                    className={`rounded-xl px-4 py-2 max-w-[85%] text-sm ${
                      m.role === "user"
                        ? "bg-slate-700 text-slate-100"
                        : "bg-slate-800 border border-slate-700 text-slate-300"
                    }`}
                  >
                    {m.role === "copilot" ? (
                      <div className="copilot-markdown prose prose-sm prose-invert max-w-none">
                        <ReactMarkdown
                          components={{
                            h1: ({ children }: { children?: React.ReactNode }) => <h3 className="text-base font-semibold text-slate-100 mt-3 mb-1">{children}</h3>,
                            h2: ({ children }: { children?: React.ReactNode }) => <h4 className="text-sm font-semibold text-slate-100 mt-3 mb-1">{children}</h4>,
                            h3: ({ children }: { children?: React.ReactNode }) => <h4 className="text-sm font-semibold text-slate-200 mt-2 mb-1">{children}</h4>,
                            p: ({ children }: { children?: React.ReactNode }) => <p className="mb-2 leading-relaxed">{children}</p>,
                            strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-semibold text-slate-100">{children}</strong>,
                            em: ({ children }: { children?: React.ReactNode }) => <em className="text-slate-300">{children}</em>,
                            ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
                            ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
                            li: ({ children }: { children?: React.ReactNode }) => <li className="text-slate-300">{children}</li>,
                            code: ({ children }: { children?: React.ReactNode }) => <code className="bg-slate-700 px-1.5 py-0.5 rounded text-teal-300 text-xs">{children}</code>,
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>
                        {m.actionProposals && m.actionProposals.length > 0 && (
                          <div className="mt-4 space-y-3">
                            {m.actionProposals.map((proposal) => (
                              <CopilotActionCard 
                                key={proposal.action_id} 
                                proposal={proposal} 
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 p-2 rounded-full bg-teal-900/50">
                  <Bot className="h-4 w-4 text-teal-400" />
                </div>
                <div className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 flex gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        <div className="p-4 bg-slate-900 border-t border-slate-800">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <Input
              value={input}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
              placeholder={isListening ? "Listening..." : "Ask about your inventory..."}
              className={`flex-1 bg-slate-800 border-slate-700 focus-visible:ring-teal-500 ${isListening ? "border-teal-500/50" : ""}`}
              disabled={isLoading}
            />
            {isSupported && (
              <Button
                type="button"
                size="icon"
                variant="outline"
                className={`flex-shrink-0 border-slate-700 ${isListening ? "bg-red-900/40 text-red-400 hover:bg-red-900/60 hover:text-red-300 animate-pulse" : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"}`}
                onClick={() => {
                  if (isListening) stopListening();
                  else startListening();
                }}
                disabled={isLoading}
              >
                {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </Button>
            )}
            <Button 
              type="submit" 
              size="icon" 
              disabled={!input.trim() || isLoading}
              className="bg-teal-600 hover:bg-teal-700 flex-shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </SheetContent>
    </Sheet>
  );
}
