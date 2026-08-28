import { useEffect, useState } from 'react'
import './App.css'

import { fetchModels } from './api/models'
import type { ModelCatalogEntry } from './types/model'

function App() {
  const [models, setModels] = useState<ModelCatalogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadModels() {
      try {
        const data = await fetchModels()
        setModels(data)
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Unable to load models.',
        )
      } finally {
        setLoading(false)
      }
    }

    void loadModels()
  }, [])

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Private LLM Platform</p>
          <h1>Model Management</h1>
          <p className="hero-copy">
            View the models available on the platform and the inference engine
            assigned to each deployment.
          </p>
        </div>

        <div className="summary-card">
          <span>Available models</span>
          <strong>{models.length}</strong>
        </div>
      </section>

      <section className="content">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Catalog</p>
            <h2>Models</h2>
          </div>

          {!loading && !error && (
            <span className="status">
              {models.filter((model) => model.enabled).length} enabled
            </span>
          )}
        </div>

        {loading && (
          <div className="state-card">
            <p>Loading model catalog...</p>
          </div>
        )}

        {error && (
          <div className="state-card error-card">
            <strong>Unable to load models</strong>
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && (
          <div className="model-grid">
            {models.map((model) => (
              <article className="model-card" key={model.model_id}>
                <div className="model-card-header">
                  <div>
                    <p className="model-id">{model.model_id}</p>
                    <h3>{model.display_name}</h3>
                  </div>

                  <span
                    className={
                      model.enabled
                        ? 'badge badge-enabled'
                        : 'badge badge-disabled'
                    }
                  >
                    {model.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>

                <dl className="model-details">
                  <div>
                    <dt>Engine</dt>
                    <dd>
                      <span className={`engine-badge engine-${model.engine}`}>
                        {model.engine}
                      </span>
                    </dd>
                  </div>

                  <div>
                    <dt>Engine model</dt>
                    <dd>{model.engine_model_id}</dd>
                  </div>

                  <div>
                    <dt>Context length</dt>
                    <dd>
                      {model.context_length
                        ? `${model.context_length.toLocaleString()} tokens`
                        : 'Not specified'}
                    </dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}

export default App