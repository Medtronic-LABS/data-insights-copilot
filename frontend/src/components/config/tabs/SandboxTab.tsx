import React, { useState, useEffect, useCallback } from 'react';
import { MessageList, ChatInput } from '../../chat';
import { 
    CommandLineIcon, 
    ChevronUpDownIcon,
    CheckIcon,
    BeakerIcon,
    ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { chatService } from '../../../services/chatService';
import { useAuth } from '../../../contexts/AuthContext';
import { getConfigHistoryPaginated, type ConfigSummary } from '../../../services/api';
import type { Agent } from '../../../types/agent';
import type { Message } from '../../../types';
import type { ActiveConfig } from '../../../contexts/AgentContext';

interface SandboxTabProps {
    agent: Agent;
    activeConfig: ActiveConfig;
}

export const SandboxTab: React.FC<SandboxTabProps> = ({
    agent,
    activeConfig
}) => {
    const { user } = useAuth();
    const [messages, setMessages] = useState<Message[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    
    // Version selector state
    const [configVersions, setConfigVersions] = useState<ConfigSummary[]>([]);
    const [selectedConfigId, setSelectedConfigId] = useState<number | null>(null);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [isLoadingVersions, setIsLoadingVersions] = useState(true);

    // Load available config versions
    const loadConfigVersions = useCallback(async () => {
        setIsLoadingVersions(true);
        try {
            // Get all configs (use large page size to get all)
            const result = await getConfigHistoryPaginated(agent.id, 1, 100);
            
            // Filter to only published configs with completed embeddings
            const testableConfigs = result.configs.filter(
                c => c.status === 'published' && c.embedding_status === 'completed'
            );
            
            setConfigVersions(testableConfigs);
            
            // Default to active config
            const active = testableConfigs.find(c => c.is_active);
            if (active) {
                setSelectedConfigId(active.id);
            } else if (testableConfigs.length > 0) {
                setSelectedConfigId(testableConfigs[0].id);
            }
        } catch (err) {
            console.error('Failed to load config versions:', err);
        } finally {
            setIsLoadingVersions(false);
        }
    }, [agent.id]);

    useEffect(() => {
        loadConfigVersions();
    }, [loadConfigVersions]);

    // Get selected config details
    const selectedConfig = configVersions.find(c => c.id === selectedConfigId);
    const isTestingNonActive = selectedConfig && !selectedConfig.is_active;

    // Handle version switch
    const handleVersionChange = (configId: number) => {
        if (configId !== selectedConfigId) {
            setSelectedConfigId(configId);
            setMessages([]); // Clear conversation when switching versions
        }
        setIsDropdownOpen(false);
    };

    const handleSend = async (content: string) => {
        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMsg]);
        setIsTyping(true);

        try {
            // Include config_id if testing a non-active version
            const response = await chatService.sendMessage({
                query: content,
                agent_id: agent.id,
                session_id: `sandbox-${agent.id}-v${selectedConfigId}`,
                ...(isTestingNonActive && selectedConfigId ? { config_id: selectedConfigId } : {})
            });

            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.answer,
                timestamp: new Date(response.timestamp),
                sources: response.sources,
                sqlQuery: response.sql_query,
                chartData: response.chart_data,
                dashboards: response.dashboards,
                traceId: response.trace_id,
                processingTime: response.processing_time
            };
            setMessages(prev => [...prev, aiMsg]);
        } catch (err: any) {
            console.error("Sandbox chat error", err);
            const errorMsg: Message = {
                id: Date.now().toString(),
                role: 'assistant',
                content: `Error: ${err.message || 'Failed to get response from agent'}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsTyping(false);
        }
    };

    const getExampleQuestions = (): string[] => {
        try {
            if (activeConfig.example_questions) {
                return JSON.parse(activeConfig.example_questions);
            }
        } catch {
            // Ignore parse errors
        }
        return [
            "What can you do?",
            "Show me the available data",
            "Summarize the recent records"
        ];
    };

    const formatVersionLabel = (config: ConfigSummary) => {
        const date = new Date(config.created_at).toLocaleDateString();
        return `v${config.version} — ${config.llm_model_name || 'Unknown model'} (${date})`;
    };

    return (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-xl overflow-hidden flex flex-col h-[700px] animate-in zoom-in-95 duration-300">
            {/* Header with version selector */}
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-start">
                    <div className="flex-1">
                        <h3 className="font-bold text-gray-900 flex items-center gap-2">
                            <CommandLineIcon className="w-5 h-5 text-indigo-600" />
                            Agent Sandbox
                        </h3>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Test configurations in real-time before activation
                        </p>
                    </div>
                    
                    {/* Version selector dropdown */}
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <button
                                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                disabled={isLoadingVersions || configVersions.length === 0}
                                className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed min-w-[220px]"
                            >
                                {isLoadingVersions ? (
                                    <span className="text-gray-400">Loading versions...</span>
                                ) : selectedConfig ? (
                                    <>
                                        <span className="flex-1 text-left truncate">
                                            {formatVersionLabel(selectedConfig)}
                                        </span>
                                        {selectedConfig.is_active && (
                                            <span className="px-1.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">
                                                Active
                                            </span>
                                        )}
                                    </>
                                ) : (
                                    <span className="text-gray-400">No versions available</span>
                                )}
                                <ChevronUpDownIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            </button>
                            
                            {/* Dropdown menu */}
                            {isDropdownOpen && configVersions.length > 0 && (
                                <>
                                    <div 
                                        className="fixed inset-0 z-10" 
                                        onClick={() => setIsDropdownOpen(false)}
                                    />
                                    <div className="absolute right-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-64 overflow-auto">
                                        <div className="p-2">
                                            <p className="px-2 py-1 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Select Config Version
                                            </p>
                                            {configVersions.map((config) => (
                                                <button
                                                    key={config.id}
                                                    onClick={() => handleVersionChange(config.id)}
                                                    className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors ${
                                                        config.id === selectedConfigId
                                                            ? 'bg-indigo-50 text-indigo-700'
                                                            : 'hover:bg-gray-50 text-gray-700'
                                                    }`}
                                                >
                                                    <div className="flex flex-col items-start">
                                                        <span className="font-medium">
                                                            Version {config.version}
                                                            {config.is_active && (
                                                                <span className="ml-2 px-1.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">
                                                                    Active
                                                                </span>
                                                            )}
                                                        </span>
                                                        <span className="text-xs text-gray-500">
                                                            {config.llm_model_name || 'Unknown model'} • {new Date(config.created_at).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                    {config.id === selectedConfigId && (
                                                        <CheckIcon className="w-4 h-4 text-indigo-600" />
                                                    )}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                        
                        <button
                            onClick={() => setMessages([])}
                            className="text-xs font-semibold text-gray-500 hover:text-red-600 transition-colors"
                        >
                            Clear Session
                        </button>
                    </div>
                </div>
                
                {/* Non-active version indicator banner */}
                {isTestingNonActive && selectedConfig && (
                    <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                        <BeakerIcon className="w-4 h-4 text-amber-600 flex-shrink-0" />
                        <span className="text-sm text-amber-800">
                            <strong>Testing Version {selectedConfig.version}</strong> — This is not the active configuration. 
                            Responses may differ from what users currently experience.
                        </span>
                    </div>
                )}
                
                {/* No testable versions warning */}
                {!isLoadingVersions && configVersions.length === 0 && (
                    <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
                        <ExclamationCircleIcon className="w-4 h-4 text-red-600 flex-shrink-0" />
                        <span className="text-sm text-red-800">
                            No testable configurations available. Ensure at least one published config has completed embeddings.
                        </span>
                    </div>
                )}
            </div>
            
            {/* Chat area */}
            <div className="flex-1 overflow-hidden flex flex-col relative bg-gray-50/30">
                <MessageList
                    messages={messages}
                    isLoading={isTyping}
                    username={user?.username}
                    onSuggestedQuestionClick={handleSend}
                    emptyStateProps={{
                        title: `Testing ${agent.name}${selectedConfig ? ` (v${selectedConfig.version})` : ''}`,
                        subtitle: isTestingNonActive 
                            ? `You're testing version ${selectedConfig?.version}, which is not currently active.`
                            : 'Type a message to see how the agent responds with its current settings.',
                        suggestions: getExampleQuestions()
                    }}
                />
            </div>
            
            {/* Input area */}
            <div className="p-4 bg-white border-t border-gray-100">
                <ChatInput
                    onSendMessage={handleSend}
                    isDisabled={isTyping || configVersions.length === 0}
                    placeholder={configVersions.length === 0 ? "No testable config available..." : "Test the agent..."}
                />
            </div>
        </div>
    );
};

export default SandboxTab;
