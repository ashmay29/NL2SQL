import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { NL2SQLResponse } from '../api/types';

interface ConversationTurn {
  query: string;
  sql: string;
  confidence: number;
  timestamp: string;
  complexity?: string;
  executionTime?: number;
  response?: NL2SQLResponse;
}

interface NL2SQLState {
  // Current session
  conversationId: string;
  currentQuery: string;
  currentResponse: NL2SQLResponse | null;
  isLoading: boolean;
  error: string | null;
  
  // Conversation history
  conversationHistory: ConversationTurn[];
  
  // UI state
  showFeedbackForm: boolean;
  showClarificationPanel: boolean;
  
  // Results
  queryResults: {
    data: Record<string, any>[];
    columns: string[];
    totalRows?: number;
    isLoading: boolean;
    error?: string;
  };
}

type NL2SQLAction =
  | { type: 'SET_CONVERSATION_ID'; payload: string }
  | { type: 'SET_CURRENT_QUERY'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_RESPONSE'; payload: NL2SQLResponse }
  | { type: 'ADD_TO_HISTORY'; payload: ConversationTurn }
  | { type: 'CLEAR_HISTORY' }
  | { type: 'SHOW_FEEDBACK_FORM'; payload: boolean }
  | { type: 'SHOW_CLARIFICATION_PANEL'; payload: boolean }
  | { type: 'SET_QUERY_RESULTS'; payload: Partial<NL2SQLState['queryResults']> }
  | { type: 'RESET_SESSION' };

const initialState: NL2SQLState = {
  conversationId: 'default',
  currentQuery: '',
  currentResponse: null,
  isLoading: false,
  error: null,
  conversationHistory: [],
  showFeedbackForm: false,
  showClarificationPanel: false,
  queryResults: {
    data: [],
    columns: [],
    isLoading: false,
  },
};

function nl2sqlReducer(state: NL2SQLState, action: NL2SQLAction): NL2SQLState {
  switch (action.type) {
    case 'SET_CONVERSATION_ID':
      return {
        ...state,
        conversationId: action.payload,
        conversationHistory: [], // Clear history for new conversation
        currentResponse: null,
        error: null,
      };
      
    case 'SET_CURRENT_QUERY':
      return {
        ...state,
        currentQuery: action.payload,
        error: null,
      };
      
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
        error: action.payload ? null : state.error, // Clear error when starting new request
      };
      
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false,
      };
      
    case 'SET_RESPONSE':
      return {
        ...state,
        currentResponse: action.payload,
        isLoading: false,
        error: null,
        showClarificationPanel: action.payload.explanations.length > 0 && !action.payload.sql,
      };
      
    case 'ADD_TO_HISTORY':
      return {
        ...state,
        conversationHistory: [...state.conversationHistory, action.payload],
      };
      
    case 'CLEAR_HISTORY':
      return {
        ...state,
        conversationHistory: [],
        currentResponse: null,
        error: null,
      };
      
    case 'SHOW_FEEDBACK_FORM':
      return {
        ...state,
        showFeedbackForm: action.payload,
      };
      
    case 'SHOW_CLARIFICATION_PANEL':
      return {
        ...state,
        showClarificationPanel: action.payload,
      };
      
    case 'SET_QUERY_RESULTS':
      return {
        ...state,
        queryResults: {
          ...state.queryResults,
          ...action.payload,
        },
      };
      
    case 'RESET_SESSION':
      return {
        ...initialState,
        conversationId: `conv-${Date.now()}`,
      };
      
    default:
      return state;
  }
}

interface NL2SQLContextType {
  state: NL2SQLState;
  dispatch: React.Dispatch<NL2SQLAction>;
  
  // Convenience methods
  setConversationId: (id: string) => void;
  setCurrentQuery: (query: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setResponse: (response: NL2SQLResponse) => void;
  addToHistory: (turn: ConversationTurn) => void;
  clearHistory: () => void;
  showFeedbackForm: (show: boolean) => void;
  showClarificationPanel: (show: boolean) => void;
  setQueryResults: (results: Partial<NL2SQLState['queryResults']>) => void;
  resetSession: () => void;
}

const NL2SQLContext = createContext<NL2SQLContextType | undefined>(undefined);

export const NL2SQLProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(nl2sqlReducer, initialState);
  
  const contextValue: NL2SQLContextType = {
    state,
    dispatch,
    
    // Convenience methods
    setConversationId: (id: string) => dispatch({ type: 'SET_CONVERSATION_ID', payload: id }),
    setCurrentQuery: (query: string) => dispatch({ type: 'SET_CURRENT_QUERY', payload: query }),
    setLoading: (loading: boolean) => dispatch({ type: 'SET_LOADING', payload: loading }),
    setError: (error: string | null) => dispatch({ type: 'SET_ERROR', payload: error }),
    setResponse: (response: NL2SQLResponse) => dispatch({ type: 'SET_RESPONSE', payload: response }),
    addToHistory: (turn: ConversationTurn) => dispatch({ type: 'ADD_TO_HISTORY', payload: turn }),
    clearHistory: () => dispatch({ type: 'CLEAR_HISTORY' }),
    showFeedbackForm: (show: boolean) => dispatch({ type: 'SHOW_FEEDBACK_FORM', payload: show }),
    showClarificationPanel: (show: boolean) => dispatch({ type: 'SHOW_CLARIFICATION_PANEL', payload: show }),
    setQueryResults: (results: Partial<NL2SQLState['queryResults']>) => dispatch({ type: 'SET_QUERY_RESULTS', payload: results }),
    resetSession: () => dispatch({ type: 'RESET_SESSION' }),
  };
  
  return (
    <NL2SQLContext.Provider value={contextValue}>
      {children}
    </NL2SQLContext.Provider>
  );
};

export const useNL2SQL = (): NL2SQLContextType => {
  const context = useContext(NL2SQLContext);
  if (!context) {
    throw new Error('useNL2SQL must be used within a NL2SQLProvider');
  }
  return context;
};
