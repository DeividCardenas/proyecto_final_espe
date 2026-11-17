/**
 * Traducción al español de las categorías del portal de datos de Chicago (vienen en inglés
 * y en mayúsculas). Lo que no esté en el diccionario se muestra en minúsculas, tal cual.
 */

export const WEATHER_ES: Record<string, string> = {
  CLEAR: "Despejado", RAIN: "Lluvia", SNOW: "Nieve", CLOUDY: "Nublado", "CLOUDY/OVERCAST": "Nublado",
  UNKNOWN: "Desconocido", OTHER: "Otro", "FREEZING RAIN/DRIZZLE": "Lluvia helada", "FOG/SMOKE/HAZE": "Niebla",
  "SLEET/HAIL": "Aguanieve / granizo", "BLOWING SNOW": "Ventisca", "SEVERE CROSS WIND GATE": "Viento cruzado",
  "BLOWING SAND, SOIL, DIRT": "Polvo",
};

export const CRASH_TYPE_ES: Record<string, string> = {
  PEDESTRIAN: "Atropello a peatón",
  PEDALCYCLIST: "Contra ciclista",
  ANGLE: "En ángulo",
  "REAR END": "Por alcance",
  TURNING: "Al girar",
  "HEAD ON": "Frontal",
  "FIXED OBJECT": "Contra objeto fijo",
  "SIDESWIPE SAME DIRECTION": "Roce lateral, mismo sentido",
  "SIDESWIPE OPPOSITE DIRECTION": "Roce lateral, sentido opuesto",
  "PARKED MOTOR VEHICLE": "Contra vehículo estacionado",
  "REAR TO FRONT": "Trasera contra frontal",
  "REAR TO SIDE": "Trasera contra lateral",
  "REAR TO REAR": "Trasera contra trasera",
  "OTHER OBJECT": "Contra otro objeto",
  "OTHER NONCOLLISION": "Sin colisión (otro)",
  OVERTURNED: "Volcamiento",
  ANIMAL: "Contra animal",
  TRAIN: "Contra tren",
};

export const CAUSE_ES: Record<string, string> = {
  "UNABLE TO DETERMINE": "Sin determinar",
  "NOT APPLICABLE": "No aplica",
  UNKNOWN: "Desconocida",
  "FAILING TO YIELD RIGHT-OF-WAY": "No ceder el paso",
  "FOLLOWING TOO CLOSELY": "No guardar distancia",
  "IMPROPER OVERTAKING/PASSING": "Adelantamiento indebido",
  "FAILING TO REDUCE SPEED TO AVOID CRASH": "No reducir la velocidad a tiempo",
  "IMPROPER BACKING": "Marcha atrás indebida",
  "IMPROPER LANE USAGE": "Uso indebido del carril",
  "IMPROPER TURNING/NO SIGNAL": "Giro indebido o sin señalizar",
  "DRIVING SKILLS/KNOWLEDGE/EXPERIENCE": "Falta de pericia al conducir",
  "DISREGARDING TRAFFIC SIGNALS": "Ignorar el semáforo",
  WEATHER: "Clima",
  "OPERATING VEHICLE IN ERRATIC, RECKLESS, CARELESS, NEGLIGENT OR AGGRESSIVE MANNER": "Conducción temeraria o agresiva",
  "DISREGARDING STOP SIGN": "Ignorar la señal de pare",
  "DISTRACTION - FROM INSIDE VEHICLE": "Distracción dentro del vehículo",
  "DISTRACTION - FROM OUTSIDE VEHICLE": "Distracción fuera del vehículo",
  "DISTRACTION - OTHER ELECTRONIC DEVICE (NAVIGATION DEVICE, DVD PLAYER, ETC.)": "Distracción con dispositivo electrónico",
  "EQUIPMENT - VEHICLE CONDITION": "Fallo mecánico del vehículo",
  "PHYSICAL CONDITION OF DRIVER": "Condición física del conductor",
  "VISION OBSCURED (SIGNS, TREE LIMBS, BUILDINGS, ETC.)": "Visibilidad obstruida",
  "UNDER THE INFLUENCE OF ALCOHOL/DRUGS (USE WHEN ARREST IS EFFECTED)": "Alcohol o drogas (con arresto)",
  "HAD BEEN DRINKING (USE WHEN ARREST IS NOT MADE)": "Había bebido (sin arresto)",
  "DRIVING ON WRONG SIDE/WRONG WAY": "Circular en contravía",
  "EXCEEDING AUTHORIZED SPEED LIMIT": "Exceso del límite de velocidad",
  "EXCEEDING SAFE SPEED FOR CONDITIONS": "Velocidad inadecuada para las condiciones",
  "ROAD ENGINEERING/SURFACE/MARKING DEFECTS": "Defectos de la vía o la señalización",
  "ROAD CONSTRUCTION/MAINTENANCE": "Obra o mantenimiento vial",
  "DISREGARDING OTHER TRAFFIC SIGNS": "Ignorar otras señales",
  "DISREGARDING ROAD MARKINGS": "Ignorar las marcas viales",
  "DISREGARDING YIELD SIGN": "Ignorar la señal de ceda el paso",
  "CELL PHONE USE OTHER THAN TEXTING": "Uso del celular (sin mensajes)",
  TEXTING: "Escribir mensajes",
  "EVASIVE ACTION DUE TO ANIMAL, OBJECT, NONMOTORIST": "Maniobra evasiva (animal, objeto o peatón)",
  ANIMAL: "Animal en la vía",
  "TURNING RIGHT ON RED": "Giro a la derecha en rojo",
  "RELATED TO BUS STOP": "Relacionada con parada de bus",
  "PASSING STOPPED SCHOOL BUS": "Adelantar un bus escolar detenido",
  "OBSTRUCTED CROSSWALKS": "Paso peatonal obstruido",
  "BICYCLE ADVANCING LEGALLY ON RED LIGHT": "Bicicleta que avanza en rojo (legal)",
  "MOTORCYCLE ADVANCING LEGALLY ON RED LIGHT": "Moto que avanza en rojo (legal)",
};

export const LIGHTING_ES: Record<string, string> = {
  DAYLIGHT: "Día", DARKNESS: "Noche oscura", "DARKNESS, LIGHTED ROAD": "Noche iluminada",
  DUSK: "Atardecer", DAWN: "Amanecer", UNKNOWN: "Desconocida",
};

const fallback = (s: string) => (s ? s.charAt(0) + s.slice(1).toLowerCase() : "");

export const weatherEs = (s: string | null | undefined) => (s ? WEATHER_ES[s] ?? fallback(s) : "");
export const crashTypeEs = (s: string | null | undefined) => (s ? CRASH_TYPE_ES[s] ?? fallback(s) : "");
export const causeEs = (s: string | null | undefined) => (s ? CAUSE_ES[s] ?? fallback(s) : "");
export const lightingEs = (s: string | null | undefined) => (s ? LIGHTING_ES[s] ?? fallback(s) : "");
