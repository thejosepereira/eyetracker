import React, { useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../../App";
import { S, C } from "./styles";
import { EyePrescription, VisionProfile } from "../models/types";

type Props = NativeStackScreenProps<RootStackParamList, "VisionProfile">;

function EyeInputs({ label, value, onChange }: {
  label: string; value: EyePrescription; onChange: (v: EyePrescription) => void;
}) {
  const num = (t: string) => (t === "" || t === "-" ? 0 : parseFloat(t));
  return (
    <View style={S.card}>
      <Text style={[S.label, { marginTop: 0, color: C.fg, fontSize: 14 }]}>{label}</Text>
      <View style={S.row}>
        {(["sphere", "cylinder", "axis"] as const).map((k) => (
          <View style={S.col} key={k}>
            <Text style={S.label}>{k[0].toUpperCase() + k.slice(1)}</Text>
            <TextInput
              style={S.input}
              keyboardType="numbers-and-punctuation"
              defaultValue={String(value[k])}
              onChangeText={(t) => onChange({ ...value, [k]: num(t) })}
            />
          </View>
        ))}
      </View>
    </View>
  );
}

export default function VisionProfileScreen({ navigation }: Props) {
  const [right, setRight] = useState<EyePrescription>({ sphere: -2.5, cylinder: -1.0, axis: 110 });
  const [left, setLeft] = useState<EyePrescription>({ sphere: -2.25, cylinder: -0.75, axis: 70 });
  const [distanceCm, setDistanceCm] = useState("35");

  async function save() {
    const profile: VisionProfile = {
      id: "default",
      name: "My Vision",
      rightEye: right,
      leftEye: left,
      viewingDistanceMm: (parseFloat(distanceCm) || 35) * 10,
    };
    await AsyncStorage.setItem("visionProfile", JSON.stringify(profile));
    navigation.navigate("Calibration");
  }

  return (
    <ScrollView style={S.screen}>
      <Text style={S.subtitle}>Enter your prescription for each eye.</Text>
      <EyeInputs label="RIGHT EYE (OD)" value={right} onChange={setRight} />
      <EyeInputs label="LEFT EYE (OS)" value={left} onChange={setLeft} />

      <Text style={S.label}>Typical viewing distance (cm)</Text>
      <TextInput style={S.input} keyboardType="number-pad" value={distanceCm} onChangeText={setDistanceCm} />

      <TouchableOpacity style={S.buttonSecondary} disabled>
        <Text style={S.buttonSecondaryText}>Scan Prescription (later)</Text>
      </TouchableOpacity>
      <TouchableOpacity style={S.button} onPress={save}>
        <Text style={S.buttonText}>Continue</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
