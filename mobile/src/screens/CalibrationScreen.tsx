import React, { useState } from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../../App";
import { S, C } from "./styles";

type Props = NativeStackScreenProps<RootStackParamList, "Calibration">;

/**
 * Pairwise A/B staircase (mirror of vision_engine.PairwiseStaircase). The user
 * repeatedly picks which correction strength looks clearer; the centre moves and
 * the step shrinks until it converges.
 */
export default function CalibrationScreen({ navigation }: Props) {
  const [center, setCenter] = useState(1.0);
  const [step, setStep] = useState(0.4);
  const minStep = 0.05;

  const lo = Math.max(0, center - step);
  const hi = center + step;
  const converged = step <= minStep;

  function choose(value: number) {
    setCenter(Math.max(0, value));
    setStep((s) => Math.max(minStep, s * 0.6));
  }

  return (
    <View style={S.screen}>
      <Text style={S.subtitle}>Which looks clearer?</Text>

      <View style={S.row}>
        {[["A", lo], ["B", hi]].map(([label, val]) => (
          <TouchableOpacity key={label as string} style={[S.card, S.col, { alignItems: "center" }]}
            onPress={() => choose(val as number)}>
            <Text style={{ color: C.fg, fontSize: 40, fontWeight: "700", letterSpacing: 3 }}>ABCD</Text>
            <Text style={{ color: C.muted, marginTop: 8 }}>Option {label as string}</Text>
            <Text style={{ color: C.muted, fontSize: 12 }}>strength {(val as number).toFixed(2)}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={[S.disclaimer, { marginTop: 16 }]}>
        Current best estimate: {center.toFixed(2)} · step {step.toFixed(2)}
      </Text>

      <TouchableOpacity style={S.button} onPress={() => navigation.navigate("Demo")}>
        <Text style={S.buttonText}>{converged ? "Done — See Demo" : "Skip to Demo"}</Text>
      </TouchableOpacity>
    </View>
  );
}
