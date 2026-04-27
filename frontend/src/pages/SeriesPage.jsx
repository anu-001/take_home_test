import { useEffect, useState } from "react";
import { format } from "date-fns";

import { seriesApi } from "../api/client";

const PLATFORMS = ["youtube", "instagram", "twitter", "tiktok", "linkedin"];
const CADENCES = ["daily", "weekly"];

export default function SeriesPage() {
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generatingSeriesId, setGeneratingSeriesId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    name: "",
    platform: "linkedin",
    start_at: "",
    cadence: "daily",
    total_posts: 4,
    status: "draft",
  });

  const loadSeries = async () => {
    try {
      const data = await seriesApi.list();
      setSeries(data);
    } catch (err) {
      setError(err.message || "Failed to load series");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSeries();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await seriesApi.create({
        ...form,
        start_at: new Date(form.start_at).toISOString(),
        total_posts: Number(form.total_posts),
      });
      setForm((prev) => ({ ...prev, name: "", start_at: "", total_posts: 4 }));
      setNotice("Series created. Generate posts when you're ready.");
      await loadSeries();
    } catch (err) {
      setError(err.message || "Failed to create series");
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async (id) => {
    setError("");
    setNotice("");
    setGeneratingSeriesId(id);
    try {
      await seriesApi.generate(id);
      setNotice("Posts generated successfully.");
      await loadSeries();
    } catch (err) {
      setError(err.message || "Failed to generate posts");
    } finally {
      setGeneratingSeriesId(null);
    }
  };

  return (
    <div className="series-page">
      <div className="page-header">
        <h1>Content Series</h1>
      </div>

      <form onSubmit={handleCreate} className="post-form">
        {error && <div className="error">{error}</div>}
        {notice && <div className="notice">{notice}</div>}
        <label>
          Series name
          <input
            type="text"
            placeholder="Launch Week"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
        </label>
        <label>
          Platform
          <select
            value={form.platform}
            onChange={(e) => setForm((prev) => ({ ...prev, platform: e.target.value }))}
          >
            {PLATFORMS.map((platform) => (
              <option key={platform} value={platform}>
                {platform}
              </option>
            ))}
          </select>
        </label>
        <label>
          Start at
          <input
            type="datetime-local"
            value={form.start_at}
            onChange={(e) => setForm((prev) => ({ ...prev, start_at: e.target.value }))}
            required
          />
        </label>
        <label>
          Cadence
          <select
            value={form.cadence}
            onChange={(e) => setForm((prev) => ({ ...prev, cadence: e.target.value }))}
          >
            {CADENCES.map((cadence) => (
              <option key={cadence} value={cadence}>
                {cadence}
              </option>
            ))}
          </select>
        </label>
        <label>
          Total posts
          <input
            type="number"
            min={1}
            max={30}
            value={form.total_posts}
            onChange={(e) => setForm((prev) => ({ ...prev, total_posts: e.target.value }))}
            required
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn primary" disabled={saving}>
            {saving ? "Creating..." : "Create Series"}
          </button>
        </div>
      </form>

      <div className="table-wrap series-table-wrap">
        {loading ? (
          <div className="loading">Loading series...</div>
        ) : (
          <table className="posts-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Platform</th>
                <th>Start</th>
                <th>Cadence</th>
                <th>Total Posts</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {series.length === 0 ? (
                <tr>
                  <td colSpan={6}>No series yet. Create one above.</td>
                </tr>
              ) : (
                series.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.platform}</td>
                    <td>{format(new Date(item.start_at), "MMM d, yyyy HH:mm")}</td>
                    <td>{item.cadence}</td>
                    <td>{item.total_posts}</td>
                    <td>
                      <button
                        type="button"
                        className="btn small"
                        onClick={() => handleGenerate(item.id)}
                        disabled={generatingSeriesId === item.id}
                      >
                        {generatingSeriesId === item.id ? "Generating..." : "Generate posts"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
