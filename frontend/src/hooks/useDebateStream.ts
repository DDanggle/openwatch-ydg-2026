import { create } from 'zustand'
import type { AgentMessage, AgentRole } from '../api/types'

interface DebateStore {
  messages: Record<AgentRole, AgentMessage>
  isStreaming: boolean
  followupQuestions: string[]
  disclaimer: string

  startDebate: (politicianId: string, topic?: string) => void
  sendFollowup: (politicianId: string, question: string) => void
  reset: () => void
}

const DEFAULT_MESSAGES: Record<AgentRole, AgentMessage> = {
  suspicion: { role: 'suspicion', displayName: '파란장미', emoji: '🌹', content: '', isComplete: false, confidence: 0 },
  optimist: { role: 'optimist', displayName: '태극기전사', emoji: '🇰🇷', content: '', isComplete: false, confidence: 0 },
  factcheck: { role: 'factcheck', displayName: '논두렁회계사', emoji: '🌾', content: '', isComplete: false, confidence: 0 },
}

const API = 'http://localhost:8010/api'

async function streamDebate(
  url: string,
  body: unknown,
  set: (fn: (state: DebateStore) => Partial<DebateStore>) => void,
) {
  set(() => ({
    messages: {
      suspicion: { ...DEFAULT_MESSAGES.suspicion },
      optimist: { ...DEFAULT_MESSAGES.optimist },
      factcheck: { ...DEFAULT_MESSAGES.factcheck },
    },
    isStreaming: true,
    followupQuestions: [],
    disclaimer: '',
  }))

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!res.ok || !res.body) {
      set(() => ({ isStreaming: false }))
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      while (buffer.includes('\n\n')) {
        const idx = buffer.indexOf('\n\n')
        const block = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)

        const lines = block.trim().split('\n')
        let eventType = ''
        let dataStr = ''
        for (const line of lines) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim()
          else if (line.startsWith('data:')) dataStr = line.slice(5).trim()
        }

        if (!dataStr) continue
        let data: Record<string, unknown>
        try { data = JSON.parse(dataStr) } catch { continue }

        const agent = data.agent as AgentRole | undefined

        if (eventType === 'agent_start' && agent) {
          set((state) => ({
            messages: {
              ...state.messages,
              [agent]: {
                ...state.messages[agent],
                displayName: (data.display_name as string) || state.messages[agent].displayName,
                emoji: (data.emoji as string) || state.messages[agent].emoji,
              },
            },
          }))
        } else if (eventType === 'agent_token' && agent && typeof data.token === 'string') {
          set((state) => ({
            messages: {
              ...state.messages,
              [agent]: {
                ...state.messages[agent],
                content: state.messages[agent].content + data.token,
              },
            },
          }))
        } else if (eventType === 'agent_done' && agent) {
          set((state) => ({
            messages: {
              ...state.messages,
              [agent]: {
                ...state.messages[agent],
                isComplete: true,
                confidence: (data.confidence as number) || 0.5,
              },
            },
          }))
        } else if (eventType === 'debate_complete') {
          set(() => ({
            followupQuestions: (data.followup_questions as string[]) || [],
            disclaimer: (data.disclaimer as string) || '',
            isStreaming: false,
          }))
        }
      }
    }

    set(() => ({ isStreaming: false }))
  } catch (err) {
    console.error('Debate stream error:', err)
    set(() => ({ isStreaming: false }))
  }
}

export const useDebateStore = create<DebateStore>((set) => ({
  messages: { ...DEFAULT_MESSAGES },
  isStreaming: false,
  followupQuestions: [],
  disclaimer: '',

  startDebate: (politicianId: string, topic?: string) => {
    streamDebate(`${API}/debate/start`, { politician_id: politicianId, topic: topic || null }, set)
  },

  sendFollowup: (politicianId: string, question: string) => {
    streamDebate(`${API}/debate/followup`, { politician_id: politicianId, question, previous_opinions: {} }, set)
  },

  reset: () => {
    set(() => ({ messages: { ...DEFAULT_MESSAGES }, isStreaming: false, followupQuestions: [], disclaimer: '' }))
  },
}))
