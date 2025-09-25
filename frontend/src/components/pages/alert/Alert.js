import React, { useEffect, useState } from 'react';

// Public alerts page (visible to anyone) with auto-refresh
const PublicAlerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState(''); // '', 'pending', 'investigating', 'resolved', 'rejected', 'solved'

  const fetchAlerts = async () => {
    try {
      setError('');
      const params = new URLSearchParams();
      if (status) params.set('status', status);
      const res = await fetch(`/api/alerts?${params.toString()}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load alerts');
      setAlerts(data.alerts || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchAlerts();
    const id = setInterval(fetchAlerts, 15000); // auto-refresh every 15s
    return () => clearInterval(id);
  }, [status]);

  const formatDate = (d) => (d ? new Date(d).toLocaleString() : '-');

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">� Public Alerts</h1>
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-600">Filter status:</label>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="rejected">Rejected</option>
            <option value="solved">Solved</option>
          </select>
          <button onClick={fetchAlerts} className="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">Refresh</button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-600">Loading alerts...</div>
      ) : error ? (
        <div className="text-red-600">{error}</div>
      ) : alerts.length === 0 ? (
        <div className="text-gray-600">No alerts yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {alerts.map((a) => (
            <div key={a.id} className="border rounded p-4 bg-white shadow">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-lg">{a.title}</h3>
                  <p className="text-sm text-gray-700 mt-1">{a.description}</p>
                </div>
                <span className="ml-3 text-xs px-2 py-1 rounded bg-gray-200">{a.status}</span>
              </div>
              <div className="mt-2 text-xs text-gray-600 flex flex-wrap gap-3">
                <span>📍 {Number(a.latitude).toFixed(4)}, {Number(a.longitude).toFixed(4)}</span>
                <span>🏷️ {a.type}</span>
                <span>🕒 {formatDate(a.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PublicAlerts;