import { useEffect, useRef, useCallback, useState } from "react";
import { useChatStore } from "../store";

interface WSMessage {
  type: string;
  assistant_message?: string;
  ercf_stage?: string;
  persona_stage?: string;
  hint_level?: number | null;
  intervention?: Record<string, unknown> | null;
  message?: string;
}

export function useWebSocketTutor(kpId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    const token = localStorage.getItem("codepilgrim_token");
    if (!token || !kpId) return;

    const wsUrl = `ws://localhost:8000/api/v1/ws/tutor/${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: WSMessage = JSON.parse(event.data);

      if (data.type === "message" && data.assistant_message) {
        useChatStore.setState((state) => ({
          messages: [...state.messages, { role: "assistant", content: data.assistant_message! }],
          ercfStage: data.ercf_stage || state.ercfStage,
          personaStage: data.persona_stage || state.personaStage,
          hintLevel: data.hint_level ?? state.hintLevel,
          isLoading: false,
        }));
      } else if (data.type === "typing") {
        useChatStore.setState({ isLoading: true });
      } else if (data.type === "error") {
        useChatStore.setState((state) => ({
          messages: [...state.messages, { role: "assistant", content: data.message || "出错了" }],
          isLoading: false,
        }));
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, [kpId]);

  const sendMessage = useCallback(
    (message: string, kpTitle: string = "", pKnow: number = 0.2) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      useChatStore.setState((state) => ({
        messages: [...state.messages, { role: "user", content: message }],
        isLoading: true,
      }));

      wsRef.current.send(
        JSON.stringify({
          kp_id: kpId,
          kp_title: kpTitle,
          message,
          p_know: pKnow,
        })
      );
    },
    [kpId]
  );

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { isConnected, sendMessage, disconnect };
}
