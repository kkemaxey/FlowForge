import { Controls } from "./controls/Controls";
import { GridMap } from "./grid-map/GridMap";
import { LiveBoard } from "./live-board/LiveBoard";
import { WorkforcePanel } from "./workforce/WorkforcePanel";

export default function ConsolePage() {
  return (
    <main className="grid flex-1 gap-4 p-4 lg:grid-cols-2">
      <GridMap />
      <LiveBoard />
      <Controls />
      <WorkforcePanel />
    </main>
  );
}
