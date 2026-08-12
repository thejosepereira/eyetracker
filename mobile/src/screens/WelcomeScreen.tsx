import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { RootStackParamList } from "../../App";
import { S } from "./styles";

type Props = NativeStackScreenProps<RootStackParamList, "Welcome">;

export default function WelcomeScreen({ navigation }: Props) {
  return (
    <View style={[S.screen, { justifyContent: "center" }]}>
      <Text style={S.title}>VisionCorrect</Text>
      <Text style={S.subtitle}>A display that adapts to your vision.</Text>

      <TouchableOpacity style={S.button} onPress={() => navigation.navigate("VisionProfile")}>
        <Text style={S.buttonText}>Get Started</Text>
      </TouchableOpacity>
      <TouchableOpacity style={S.buttonSecondary} onPress={() => navigation.navigate("Demo")}>
        <Text style={S.buttonSecondaryText}>Learn How It Works</Text>
      </TouchableOpacity>

      <Text style={S.disclaimer}>
        Experimental vision-adaptive display technology. Not a diagnostic device or a
        replacement for prescribed corrective eyewear.
      </Text>
    </View>
  );
}
