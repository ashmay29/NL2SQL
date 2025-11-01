import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useUploadEmbeddings, useSchema } from '../api/hooks';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';

export const EmbeddingsManager = () => {
  const [jsonInput, setJsonInput] = useState('');
  const { data: schema } = useSchema();
  const uploadMutation = useUploadEmbeddings();

  const handleUpload = () => {
    try {
      const payload = JSON.parse(jsonInput);
      uploadMutation.mutate(payload);
    } catch (error) {
      alert('Invalid JSON format');
    }
  };

  const examplePayload = {
    schema_fingerprint: schema?.version || '<schema_version>',
    dim: 4,
    nodes: [
      { id: 'table:orders', vec: [0.1, 0.2, 0.3, 0.4] },
      { id: 'column:orders.order_id', vec: [0.5, 0.6, 0.7, 0.8] },
    ],
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-semibold text-apple-gray-900 mb-2">Embeddings</h1>
        <p className="text-apple-gray-500">Upload GNN embeddings for schema linking</p>
      </div>

      {/* Current Schema Info */}
      {schema && (
        <Card>
          <h2 className="text-lg font-semibold text-apple-gray-900 mb-3">Current Schema</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-apple-gray-500">Database:</span>
              <span className="font-medium text-apple-gray-900">{schema.database}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apple-gray-500">Fingerprint:</span>
              <Badge variant="info">{schema.version}</Badge>
            </div>
          </div>
        </Card>
      )}

      {/* Upload Section */}
      <Card>
        <h2 className="text-xl font-semibold text-apple-gray-900 mb-4">Upload Embeddings</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-apple-gray-700 mb-2">
              Embeddings JSON
            </label>
            <textarea
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder={JSON.stringify(examplePayload, null, 2)}
              className="w-full h-64 px-4 py-3 rounded-xl border border-apple-gray-200 bg-white text-apple-gray-900 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-apple-blue focus:border-transparent resize-none"
            />
          </div>

          <Button
            onClick={handleUpload}
            loading={uploadMutation.isPending}
            disabled={!jsonInput.trim()}
            className="w-full"
          >
            <Upload className="w-4 h-4" />
            Upload Embeddings
          </Button>
        </div>
      </Card>

      {/* Success Message */}
      {uploadMutation.isSuccess && uploadMutation.data && (
        <Card>
          <div className="flex items-start gap-3 p-4 bg-apple-green/10 border border-apple-green/20 rounded-xl">
            <CheckCircle className="w-5 h-5 text-apple-green flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-apple-green mb-2">Upload Successful!</p>
              <div className="space-y-1 text-sm text-apple-gray-700">
                <p>Schema Fingerprint: <span className="font-mono">{uploadMutation.data.schema_fingerprint}</span></p>
                <p>Nodes Count: <span className="font-semibold">{uploadMutation.data.nodes_count}</span></p>
                <p>Dimension: <span className="font-semibold">{uploadMutation.data.dim}</span></p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Error Message */}
      {uploadMutation.isError && (
        <Card>
          <div className="flex items-start gap-3 p-4 bg-apple-red/10 border border-apple-red/20 rounded-xl">
            <AlertCircle className="w-5 h-5 text-apple-red flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-apple-red mb-1">Upload Failed</p>
              <p className="text-sm text-apple-gray-700">{uploadMutation.error?.message}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Example Format */}
      <Card>
        <h2 className="text-lg font-semibold text-apple-gray-900 mb-3">Example Format</h2>
        <pre className="text-xs bg-apple-gray-50 p-4 rounded-xl overflow-x-auto font-mono">
          {JSON.stringify(examplePayload, null, 2)}
        </pre>
        <p className="mt-3 text-sm text-apple-gray-500">
          Replace <code className="px-1.5 py-0.5 bg-apple-gray-100 rounded">{'<schema_version>'}</code> with the actual schema fingerprint from above.
        </p>
      </Card>
    </div>
  );
};
