import { describe, expect, it } from "vitest";
import { applyThemeVars, THEME_ORDER, THEMES } from "@/theme/themes";

describe("temas visuales", () => {
  it("define las cuatro pieles con escalas completas", () => {
    expect(THEME_ORDER).toEqual(["tron", "cyberpunk", "nerv", "classic"]);
    for (const id of THEME_ORDER) {
      const t = THEMES[id];
      expect(Object.keys(t.slate)).toHaveLength(11);
      expect(Object.keys(t.cyan)).toHaveLength(11);
      expect(t.severity).toHaveLength(3);
      for (const v of Object.values(t.slate)) expect(v).toMatch(/^\d{1,3} \d{1,3} \d{1,3}$/);
    }
  });

  it("aplica variables CSS y el atributo data-theme", () => {
    const root = document.createElement("div");
    applyThemeVars(THEMES.nerv, root);
    expect(root.dataset.theme).toBe("nerv");
    expect(root.style.getPropertyValue("--cyan-400")).toBe("255 140 26");
    expect(root.style.getPropertyValue("--font-display")).toContain("Shippori");
  });
});
