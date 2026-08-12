import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, Image, Switch, TouchableOpacity, ActivityIndicator } from "react-native";
import * as ImagePicker from "expo-image-picker";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../../App";
import { S, C } from "./styles";
import { correctImage } from "../services/api";
import { VisionProfile, defaultCalibration } from "../models/types";

type Props = NativeStackScreenProps<RootStackParamList, "Demo">;

export default function DemoScreen({ navigation }: Props) {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [correctedUri, setCorrectedUri] = useState<string | null>(null);
  const [on, setOn] = useState(true);
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState<VisionProfile | null>(null);

  useEffect(() => {
    AsyncStorage.getItem("visionProfile").then((v) => v && setProfile(JSON.parse(v)));
  }, []);

  async function pick() {
    const res = await ImagePicker.launchImageLibraryAsync({ quality: 1 });
    if (!res.canceled) {
      setImageUri(res.assets[0].uri);
      setCorrectedUri(null);
    }
  }

  async function process() {
    if (!imageUri || !profile) return;
    setBusy(true);
    try {
      const blob = await correctImage({
        imageUri,
        prescription: profile.rightEye,
        viewingDistanceMm: profile.viewingDistanceMm,
        calibration: defaultCalibration(),
      });
      const reader = new FileReader();
      reader.onload = () => setCorrectedUri(reader.result as string);
      reader.readAsDataURL(blob);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  const shown = on && correctedUri ? correctedUri : imageUri;

  return (
    <ScrollView style={S.screen}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Text style={{ color: C.fg, fontSize: 16 }}>Vision correction</Text>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <Text style={{ color: C.muted }}>{on ? "ON" : "OFF"}</Text>
          <Switch value={on} onValueChange={setOn} />
        </View>
      </View>

      <View style={[S.card, { alignItems: "center", minHeight: 260, justifyContent: "center" }]}>
        {busy ? <ActivityIndicator color={C.accent} /> :
          shown ? <Image source={{ uri: shown }} style={{ width: "100%", height: 260, resizeMode: "contain" }} /> :
            <Text style={{ color: C.muted }}>Pick a photo to begin</Text>}
      </View>

      <TouchableOpacity style={S.buttonSecondary} onPress={pick}>
        <Text style={S.buttonSecondaryText}>Choose Photo</Text>
      </TouchableOpacity>
      <TouchableOpacity style={S.button} onPress={process} disabled={!imageUri || !profile}>
        <Text style={S.buttonText}>Apply Correction</Text>
      </TouchableOpacity>

      {!profile && (
        <Text style={S.disclaimer}>No profile yet — set one in Vision Profile first.</Text>
      )}
      <TouchableOpacity onPress={() => navigation.navigate("Settings")}>
        <Text style={[S.disclaimer, { color: C.accent }]}>Advanced settings →</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}
