import { Route, Routes } from "react-router-dom";
import { AppBar } from "@/components/AppBar";
import { DashboardPage } from "@/pages/DashboardPage";
import { RunsListPage } from "@/pages/RunsListPage";
import { RunViewPage } from "@/pages/RunViewPage";
import { BenchmarksPage } from "@/pages/BenchmarksPage";
import { DemoPage } from "@/pages/DemoPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export default function App() {
  return (
    <div className="min-h-full bg-base">
      <AppBar />
      <main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/runs" element={<RunsListPage />} />
          <Route path="/runs/:id" element={<RunViewPage />} />
          <Route path="/benchmarks" element={<BenchmarksPage />} />
          <Route path="/demo" element={<DemoPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}
