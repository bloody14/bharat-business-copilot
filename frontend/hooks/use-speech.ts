"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export type SpeechLang = "hi-IN" | "en-IN";

export interface UseSpeechProps {
  lang?: SpeechLang;
  onTranscriptChange: (text: string) => void;
  onListeningChange?: (isListening: boolean) => void;
}

export function useSpeech({ lang = "hi-IN", onTranscriptChange, onListeningChange }: UseSpeechProps) {
  const [isSupported, setIsSupported] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  
  // We need a stable ref for onTranscriptChange so the effect doesn't re-run constantly
  const callbackRef = useRef(onTranscriptChange);
  useEffect(() => {
    callbackRef.current = onTranscriptChange;
  }, [onTranscriptChange]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false; // Auto stops when speech is done
    recognition.interimResults = true;
    recognition.lang = lang;
    
    recognition.onstart = () => {
      setIsListening(true);
      onListeningChange?.(true);
      setError(null);
    };
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      for (let i = 0; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript + ' ';
        } else {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      callbackRef.current(finalTranscript);
    };
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (event: any) => {
      if (event.error === 'no-speech') return;
      setError(`Speech recognition error: ${event.error}`);
      setIsListening(false);
      onListeningChange?.(false);
    };
    
    recognition.onend = () => {
      setIsListening(false);
      onListeningChange?.(false);
    };
    
    recognitionRef.current = recognition;
    
    return () => {
      if (recognitionRef.current) {
        try {
            recognitionRef.current.abort();
        } catch {
            // ignore
        }
      }
    };
  }, [lang, onListeningChange]); // Re-init if lang changes

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.start();
    } catch {
      // Ignore if already started
    }
  }, []);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch {}
  }, []);

  return {
    isSupported,
    isListening,
    error,
    startListening,
    stopListening
  };
}
