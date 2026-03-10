/**
 * ModelCatalog Component
 * 
 * A comprehensive UI for browsing, selecting, and activating embedding models
 * from a curated catalog. Features:
 * - Pre-validated models with accurate dimensions
 * - Quality/Speed ratings for easy comparison
 * - Automatic dimension update warnings
 * - Rebuild alerts when switching models
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  getModelCatalog,
  addModelFromCatalog,
  activateEmbeddingModel,
  getEmbeddingModels,
  validateModelAvailability,
  handleApiError,
} from '../services/api';
import type { CatalogModelInfo, ModelInfo, ModelActivationResponse } from '../services/api';

interface ModelCatalogProps {
  onModelActivated?: (result: ModelActivationResponse) => void;
  readOnly?: boolean;
}

const ModelCatalog: React.FC<ModelCatalogProps> = ({ onModelActivated, readOnly = false }) => {
  // State
  const [catalog, setCatalog] = useState<CatalogModelInfo[]>([]);
  const [registeredModels, setRegisteredModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [localOnly, setLocalOnly] = useState(false);
  
  // Action state
  const [addingModel, setAddingModel] = useState<string | null>(null);
  const [activatingModel, setActivatingModel] = useState<number | null>(null);
  const [validatingModel, setValidatingModel] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<{ model: string; available: boolean; message: string } | null>(null);
  
  // Feedback
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'warning'; message: string } | null>(null);
  
  // Rebuild warning modal
  const [rebuildWarning, setRebuildWarning] = useState<ModelActivationResponse | null>(null);

  // Load catalog and registered models
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [catalogData, modelsData] = await Promise.all([
        getModelCatalog({ 
          category: categoryFilter as 'general' | 'multilingual' | 'fast' | 'medical' | undefined, 
          localOnly 
        }),
        getEmbeddingModels(),
      ]);
      setCatalog(catalogData);
      setRegisteredModels(modelsData);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, localOnly]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Add model from catalog
  const handleAddFromCatalog = async (modelName: string) => {
    setAddingModel(modelName);
    setFeedback(null);
    try {
      await addModelFromCatalog(modelName);
      setFeedback({ type: 'success', message: `Added "${modelName}" to registry` });
      await loadData();
    } catch (err) {
      setFeedback({ type: 'error', message: handleApiError(err) });
    } finally {
      setAddingModel(null);
    }
  };

  // Activate a registered model
  const handleActivate = async (modelId: number) => {
    setActivatingModel(modelId);
    setFeedback(null);
    try {
      const result = await activateEmbeddingModel(modelId);
      
      if (result.requires_rebuild) {
        setRebuildWarning(result);
      } else {
        setFeedback({ type: 'success', message: `Activated model successfully` });
      }
      
      onModelActivated?.(result);
      await loadData();
    } catch (err) {
      setFeedback({ type: 'error', message: handleApiError(err) });
    } finally {
      setActivatingModel(null);
    }
  };

  // Validate model availability
  const handleValidate = async (modelName: string) => {
    setValidatingModel(modelName);
    setValidationResult(null);
    try {
      const result = await validateModelAvailability(modelName);
      setValidationResult({ model: modelName, ...result });
    } catch (err) {
      setValidationResult({ model: modelName, available: false, message: handleApiError(err) });
    } finally {
      setValidatingModel(null);
    }
  };

  const activeModel = registeredModels.find(m => m.is_active === 1);

  const RatingStars: React.FC<{ rating: number; label: string }> = ({ rating, label }) => (
    <div className="flex items-center gap-1">
      <span className="text-[10px] text-gray-500 w-12">{label}:</span>
      <div className="flex">
        {[1, 2, 3, 4, 5].map(i => (
          <svg key={i} className={`w-3 h-3 ${i <= rating ? 'text-yellow-400' : 'text-gray-200'}`} fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        ))}
      </div>
    </div>
  );

  const categoryColors: Record<string, string> = {
    general: 'bg-blue-100 text-blue-700',
    multilingual: 'bg-purple-100 text-purple-700',
    fast: 'bg-green-100 text-green-700',
    medical: 'bg-red-100 text-red-700',
    code: 'bg-orange-100 text-orange-700',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Embedding Model Catalog</h2>
          <p className="text-sm text-gray-500">Pre-validated models with accurate dimensions</p>
        </div>
        {activeModel && (
          <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-green-800">Active: {activeModel.display_name}</span>
            <span className="text-xs text-green-600">({activeModel.dimensions}d)</span>
          </div>
        )}
      </div>

      {/* Feedback Toast */}
      {feedback && (
        <div className={`px-4 py-3 rounded-lg text-sm font-medium flex items-center gap-2 ${
          feedback.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
          feedback.type === 'warning' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
          'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {feedback.type === 'success' ? '✓' : feedback.type === 'warning' ? '⚠️' : '✗'} {feedback.message}
          <button onClick={() => setFeedback(null)} className="ml-auto text-current opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      {/* Rebuild Warning Modal */}
      {rebuildWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-100 rounded-full">
                <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Vector Database Rebuild Required</h3>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800 font-medium mb-2">Dimension Change Detected</p>
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-1 bg-gray-100 rounded font-mono">{rebuildWarning.previous_dimensions}d</span>
                  <span className="text-gray-400">→</span>
                  <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded font-mono">{rebuildWarning.new_dimensions}d</span>
                </div>
              </div>
              <p className="text-sm text-gray-600">{rebuildWarning.rebuild_warning}</p>
              <button onClick={() => setRebuildWarning(null)} className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium text-sm">
                I Understand
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <label htmlFor="category-filter" className="text-sm text-gray-600">Category:</label>
          <select 
            id="category-filter"
            title="Filter by model category"
            value={categoryFilter} 
            onChange={(e) => setCategoryFilter(e.target.value)} 
            className="text-sm border-gray-300 rounded-md px-3 py-1.5 border"
          >
            <option value="">All Categories</option>
            <option value="general">General Purpose</option>
            <option value="multilingual">Multilingual</option>
            <option value="fast">Fast / Lightweight</option>
          </select>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={localOnly} onChange={(e) => setLocalOnly(e.target.checked)} className="rounded border-gray-300 text-indigo-600" />
          <span className="text-sm text-gray-600">Local models only (no API key)</span>
        </label>
        <button onClick={loadData} disabled={loading} className="ml-auto text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1">
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">{error}</div>}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <svg className="animate-spin h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )}

      {/* Catalog Grid */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {catalog.map((model) => {
            const isRegistered = model.is_registered;
            const registeredModel = registeredModels.find(m => m.model_name === model.model_name);
            const isActive = registeredModel?.is_active === 1;
            const isAdding = addingModel === model.catalog_key;
            const isActivating = activatingModel === registeredModel?.id;
            const isValidating = validatingModel === model.model_name;
            
            return (
              <div key={model.catalog_key} className={`relative p-4 rounded-xl border-2 transition-all ${isActive ? 'border-green-400 bg-green-50' : isRegistered ? 'border-indigo-200 bg-indigo-50/30' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
                {isActive && <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-green-500 text-white text-[10px] font-bold rounded-full">ACTIVE</div>}
                {isRegistered && !isActive && <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-indigo-500 text-white text-[10px] font-bold rounded-full">REGISTERED</div>}

                <div className="mb-3">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900 text-sm">{model.display_name}</h3>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${categoryColors[model.category] || 'bg-gray-100'}`}>{model.category}</span>
                  </div>
                  <p className="text-[10px] text-gray-500 font-mono truncate">{model.model_name}</p>
                </div>

                <p className="text-xs text-gray-600 mb-3 line-clamp-2">{model.description}</p>

                <div className="grid grid-cols-2 gap-2 mb-3 text-[10px]">
                  <div className="px-2 py-1 bg-gray-100 rounded"><span className="text-gray-500">Dim:</span> <span className="font-semibold">{model.dimensions}d</span></div>
                  <div className="px-2 py-1 bg-gray-100 rounded"><span className="text-gray-500">Tokens:</span> <span className="font-semibold">{model.max_tokens}</span></div>
                  <div className="px-2 py-1 bg-gray-100 rounded"><span className="text-gray-500">Type:</span> <span className={`font-semibold ${model.local ? 'text-green-700' : 'text-blue-700'}`}>{model.local ? 'Local' : 'API'}</span></div>
                  {model.model_size_mb && <div className="px-2 py-1 bg-gray-100 rounded"><span className="text-gray-500">Size:</span> <span className="font-semibold">{model.model_size_mb}MB</span></div>}
                </div>

                <div className="flex flex-col gap-1 mb-3">
                  <RatingStars rating={model.quality_rating} label="Quality" />
                  <RatingStars rating={model.speed_rating} label="Speed" />
                </div>

                {model.requires_api_key && (
                  <div className="flex items-center gap-1 text-[10px] text-amber-600 mb-3">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
                    Requires API key
                  </div>
                )}

                {validationResult && validationResult.model === model.model_name && (
                  <div className={`text-[10px] p-2 rounded mb-3 ${validationResult.available ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                    {validationResult.available ? '✓' : '✗'} {validationResult.message}
                  </div>
                )}

                <div className="flex gap-2">
                  {!isRegistered ? (
                    <>
                      <button onClick={() => handleValidate(model.model_name)} disabled={readOnly || isValidating} className="flex-1 px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50 flex items-center justify-center gap-1">
                        {isValidating ? <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /></svg> : '✓'} Validate
                      </button>
                      <button onClick={() => handleAddFromCatalog(model.catalog_key)} disabled={readOnly || isAdding} className="flex-1 px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50 flex items-center justify-center gap-1">
                        {isAdding ? <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /></svg> : '+'} Add
                      </button>
                    </>
                  ) : !isActive ? (
                    <button onClick={() => registeredModel && handleActivate(registeredModel.id)} disabled={readOnly || isActivating} className="w-full px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50">
                      {isActivating ? 'Activating...' : 'Activate Model'}
                    </button>
                  ) : (
                    <div className="w-full px-3 py-1.5 text-xs text-center text-green-700 bg-green-100 rounded-lg font-medium">Currently Active</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && catalog.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No models match your filters</p>
          <button onClick={() => { setCategoryFilter(''); setLocalOnly(false); }} className="mt-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium">Clear filters</button>
        </div>
      )}
    </div>
  );
};

export default ModelCatalog;
