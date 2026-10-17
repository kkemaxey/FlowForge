import { Card } from "@/components/ui/Card";

type LocationKind =
  | "storage"
  | "pick_station"
  | "pack_station"
  | "dock"
  | "charger";

type WarehouseLocation = {
  id: number;
  code: string;
  x: number;
  y: number;
  kind: LocationKind;
  zone: string | null;
  aisle: string | null;
};

// Temporary sample data matching the database schema; replace with API data.
const sampleLocations: WarehouseLocation[] = [
  { id: 1, code: "ST-A1", x: 2, y: 3, kind: "storage", zone: "A", aisle: "A1" },
  { id: 2, code: "PICK-A", x: 5, y: 5, kind: "pick_station", zone: "A", aisle: null },
  { id: 3, code: "PACK-A", x: 7, y: 6, kind: "pack_station", zone: "A", aisle: null },
  { id: 4, code: "DOCK-1", x: 8, y: 2, kind: "dock", zone: null, aisle: null },
  { id: 5, code: "CHG-1", x: 1, y: 8, kind: "charger", zone: "B", aisle: null },
];

const GRID_SIZE = 10;

const kindSymbols: Record<LocationKind, string> = {
  storage: "S",
  pick_station: "P",
  pack_station: "K",
  dock: "D",
  charger: "C",
};

const kindColors: Record<LocationKind, string> = {
  storage: "#dbeafe",
  pick_station: "#dcfce7",
  pack_station: "#fef3c7",
  dock: "#f3e8ff",
  charger: "#ffedd5",
};

function hasValidCoordinates({ x, y }: WarehouseLocation) {
  return (
    Number.isInteger(x) &&
    Number.isInteger(y) &&
    x >= 0 &&
    x < GRID_SIZE &&
    y >= 0 &&
    y < GRID_SIZE
  );
}

export function GridMap() {
  const locationsByCoordinate = new Map<string, WarehouseLocation[]>();
  const invalidLocations = sampleLocations.filter(
    (location) => !hasValidCoordinates(location)
  );
  const validLocations = sampleLocations.filter(hasValidCoordinates);

  for (const location of validLocations) {
    const key = `${location.x},${location.y}`;
    const locationsAtCoordinate = locationsByCoordinate.get(key) ?? [];
    locationsAtCoordinate.push(location);
    locationsByCoordinate.set(key, locationsAtCoordinate);
  }

  const collisions = Array.from(locationsByCoordinate.entries()).filter(
    ([, locationsAtCoordinate]) => locationsAtCoordinate.length > 1
  );
  const placedLocationCount = validLocations.length;

  return (
    <Card title="Grid map">
      <div style={{ width: "100%", overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            minWidth: "390px",
            tableLayout: "fixed",
            borderCollapse: "separate",
            borderSpacing: "3px",
          }}
        >
          <caption
            style={{
              position: "absolute",
              width: "1px",
              height: "1px",
              padding: 0,
              margin: "-1px",
              overflow: "hidden",
              clip: "rect(0, 0, 0, 0)",
              whiteSpace: "nowrap",
              border: 0,
            }}
          >
            Warehouse locations by x and y coordinate. Y coordinates decrease
            from top to bottom.
          </caption>
          <colgroup>
            <col style={{ width: "28px" }} />
            {Array.from({ length: GRID_SIZE }, (_, x) => (
              <col key={`column-${x}`} />
            ))}
          </colgroup>
          <thead>
            <tr>
              <th scope="col" aria-label="Y coordinate" />
              {Array.from({ length: GRID_SIZE }, (_, x) => (
                <th
                  key={`x-${x}`}
                  scope="col"
                  style={{
                    textAlign: "center",
                    fontSize: "12px",
                    paddingBottom: "4px",
                    fontWeight: 400,
                  }}
                >
                  {x}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: GRID_SIZE }, (_, row) => {
              const y = GRID_SIZE - 1 - row;

              return (
                <tr key={`row-${y}`}>
                  <th
                    scope="row"
                    style={{
                      textAlign: "center",
                      fontSize: "12px",
                      fontWeight: 400,
                    }}
                  >
                    {y}
                  </th>
                  {Array.from({ length: GRID_SIZE }, (_, x) => {
                    const locations = locationsByCoordinate.get(`${x},${y}`) ?? [];
                    const label = locations.length
                      ? locations
                          .map(
                            (location) =>
                              `${location.code} | ${location.kind} | Zone: ${
                                location.zone ?? "N/A"
                              } | Aisle: ${location.aisle ?? "N/A"}`
                          )
                          .join("; ")
                      : `Empty location (${x}, ${y})`;

                    return (
                      <td
                        key={`cell-${x}-${y}`}
                        aria-label={`${label} | (${x}, ${y})`}
                        title={`${label} | (${x}, ${y})`}
                        style={{
                          height: "42px",
                          border: "1px solid #d1d5db",
                          borderRadius: "4px",
                          background:
                            locations.length === 1
                              ? kindColors[locations[0].kind]
                              : locations.length > 1
                                ? "#fee2e2"
                                : "#f9fafb",
                          textAlign: "center",
                          verticalAlign: "middle",
                          fontSize: "12px",
                          fontWeight: 600,
                        }}
                      >
                        {locations.map((location) => kindSymbols[location.kind]).join("")}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          marginTop: "16px",
          fontSize: "12px",
        }}
      >
        <span>🔵 S = Storage</span>
        <span>🟢 P = Pick station</span>
        <span>🟡 K = Pack station</span>
        <span>🟣 D = Dock</span>
        <span>🟠 C = Charger</span>
      </div>

      <p style={{ fontSize: "12px", marginTop: "12px" }}>
        {placedLocationCount} of {sampleLocations.length} locations placed · 10 × 10
        grid · Coordinates 0–9
      </p>

      {(invalidLocations.length > 0 || collisions.length > 0) && (
        <div
          role="status"
          aria-live="polite"
          style={{ fontSize: "12px", marginTop: "8px", color: "#b91c1c" }}
        >
          {invalidLocations.length > 0 && (
            <p>
              {invalidLocations.length === 1 ? "Location" : "Locations"} with
              invalid coordinates (not placed):{" "}
              {invalidLocations
                .map(({ code, x, y }) => `${code} (${x}, ${y})`)
                .join(", ")}
            </p>
          )}
          {collisions.length > 0 && (
            <p>
              Multiple locations share coordinates:{" "}
              {collisions
                .map(
                  ([coordinate, locationsAtCoordinate]) =>
                    `${locationsAtCoordinate.map(({ code }) => code).join(", ")} (${coordinate})`
                )
                .join("; ")}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
