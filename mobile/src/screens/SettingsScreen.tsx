import React, { useEffect, useState } from "react";
import { ScrollView, View, Text } from "react-native";
import { S, C } from "./styles";
import { API_URL, health } from "../services/api";

export default function SettingsScreen() {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => { health().then(setOk); }, []);

  const Row = ({ k, v }: { k: string; v: string }) => (
    <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 10 }}>
      <Text style={{ color: C.muted }}>{k}</Text>
      <Text style={{ color: C.fg }}>{v}</Text>
    </View>
  );

  return (
    <ScrollView style={S.screen}>
      <Text style={S.subtitle}>Advanced / diagnostics</Text>
      <View style={S.card}>
        <Row k="API URL" v={API_URL} />
        <Row k="Backend health" v={ok == null ? "checking…" : ok ? "ok" : "unreachable"} />
        <Row k="Algorithm version" v="0.1.0" />
      </View>
      <Text style={S.disclaimer}>
        The correction shown here is an experimental approximation of your eye's optics.
        It is not a diagnostic measurement and does not replace prescribed eyewear.
      </Text>
    </ScrollView>
  );
}
