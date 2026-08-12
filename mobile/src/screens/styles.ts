import { StyleSheet } from "react-native";

export const C = {
  bg: "#0f1115",
  card: "#181b22",
  line: "#2a2f3a",
  fg: "#e8eaed",
  muted: "#9aa0ab",
  accent: "#5b9dff",
};

export const S = StyleSheet.create({
  screen: { flex: 1, backgroundColor: C.bg, padding: 20 },
  title: { color: C.fg, fontSize: 26, fontWeight: "700", marginBottom: 6 },
  subtitle: { color: C.muted, fontSize: 15, marginBottom: 24 },
  label: { color: C.muted, fontSize: 12, marginTop: 14, marginBottom: 4 },
  input: {
    backgroundColor: C.card, color: C.fg, borderColor: C.line, borderWidth: 1,
    borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16,
  },
  row: { flexDirection: "row", gap: 10 },
  col: { flex: 1 },
  button: {
    backgroundColor: C.accent, borderRadius: 10, paddingVertical: 14,
    alignItems: "center", marginTop: 20,
  },
  buttonText: { color: "#031024", fontWeight: "700", fontSize: 16 },
  buttonSecondary: {
    backgroundColor: C.card, borderColor: C.line, borderWidth: 1,
    borderRadius: 10, paddingVertical: 14, alignItems: "center", marginTop: 12,
  },
  buttonSecondaryText: { color: C.fg, fontWeight: "600", fontSize: 16 },
  disclaimer: { color: C.muted, fontSize: 11, marginTop: 24, lineHeight: 16 },
  card: { backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 12, padding: 16, marginTop: 12 },
});
