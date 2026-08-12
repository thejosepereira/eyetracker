import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import WelcomeScreen from "./src/screens/WelcomeScreen";
import VisionProfileScreen from "./src/screens/VisionProfileScreen";
import CalibrationScreen from "./src/screens/CalibrationScreen";
import DemoScreen from "./src/screens/DemoScreen";
import SettingsScreen from "./src/screens/SettingsScreen";

export type RootStackParamList = {
  Welcome: undefined;
  VisionProfile: undefined;
  Calibration: undefined;
  Demo: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const theme = {
  headerStyle: { backgroundColor: "#0f1115" },
  headerTintColor: "#e8eaed",
  contentStyle: { backgroundColor: "#0f1115" },
};

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Welcome" screenOptions={theme}>
        <Stack.Screen name="Welcome" component={WelcomeScreen} options={{ headerShown: false }} />
        <Stack.Screen name="VisionProfile" component={VisionProfileScreen} options={{ title: "Vision Profile" }} />
        <Stack.Screen name="Calibration" component={CalibrationScreen} options={{ title: "Calibration" }} />
        <Stack.Screen name="Demo" component={DemoScreen} options={{ title: "Demo" }} />
        <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: "Advanced" }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
