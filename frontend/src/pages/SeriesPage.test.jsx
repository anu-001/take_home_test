import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import SeriesPage from "./SeriesPage";

vi.mock("../api/client", () => ({
  seriesApi: {
    list: vi.fn(),
    create: vi.fn(),
    generate: vi.fn(),
  },
}));

const { seriesApi } = await import("../api/client");

describe("SeriesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and renders existing series rows", async () => {
    seriesApi.list.mockResolvedValueOnce([
      {
        id: 7,
        name: "Launch Week",
        platform: "linkedin",
        start_at: "2026-06-01T10:00:00Z",
        cadence: "daily",
        total_posts: 4,
      },
    ]);

    render(<SeriesPage />);

    expect(await screen.findByText("Launch Week")).toBeInTheDocument();
    expect(screen.getAllByText("linkedin").length).toBeGreaterThan(0);
    expect(seriesApi.list).toHaveBeenCalledTimes(1);
  });

  it("submits a normalized payload and reloads list", async () => {
    seriesApi.list.mockResolvedValue([]);
    seriesApi.create.mockResolvedValue({ id: 9 });

    render(<SeriesPage />);

    fireEvent.change(screen.getByLabelText("Series name"), { target: { value: "Launch Week" } });
    fireEvent.change(screen.getByLabelText("Start at"), { target: { value: "2026-06-01T10:00" } });
    fireEvent.change(screen.getByLabelText("Total posts"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Series" }));

    await waitFor(() => {
      expect(seriesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Launch Week",
          total_posts: 5,
          status: "draft",
        })
      );
    });
    await waitFor(() => {
      expect(seriesApi.list).toHaveBeenCalledTimes(2);
    });
  });

  it("disables generate button during request", async () => {
    let resolveGenerate;
    seriesApi.list.mockResolvedValue([
      {
        id: 12,
        name: "Launch Week",
        platform: "linkedin",
        start_at: "2026-06-01T10:00:00Z",
        cadence: "daily",
        total_posts: 4,
      },
    ]);
    seriesApi.generate.mockReturnValue(
      new Promise((resolve) => {
        resolveGenerate = resolve;
      })
    );

    render(<SeriesPage />);
    const button = await screen.findByRole("button", { name: "Generate posts" });
    fireEvent.click(button);

    expect(seriesApi.generate).toHaveBeenCalledWith(12);
    expect(button).toBeDisabled();
    expect(screen.getByRole("button", { name: "Generating..." })).toBeInTheDocument();

    resolveGenerate([]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Generate posts" })).toBeInTheDocument();
    });
  });
});
