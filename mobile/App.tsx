import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider, useAuth } from './src/auth';
import { colors } from './src/ui';
import { RootParamList } from './src/navigation';
import { AccountScreen } from './src/screens/AccountScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { InspectionScreen } from './src/screens/InspectionScreen';
import { LoginScreen } from './src/screens/LoginScreen';
import { PropertiesScreen } from './src/screens/PropertiesScreen';
import { RegisterScreen } from './src/screens/RegisterScreen';
import { TenancyScreen } from './src/screens/TenancyScreen';

const Stack = createNativeStackNavigator<RootParamList>();

const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.canvas,
    primary: colors.accent,
    text: colors.ink,
    card: colors.card,
    border: colors.line,
    notification: colors.amber,
  },
};

function Routes() {
  const { user, ready } = useAuth();
  if (!ready) {
    return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.canvas }}><ActivityIndicator color={colors.accent} /></View>;
  }
  return (
    <Stack.Navigator screenOptions={{
      headerTintColor: colors.ink,
      headerShadowVisible: false,
      headerStyle: { backgroundColor: colors.card },
      headerTitleStyle: { color: colors.ink, fontWeight: '600' },
      contentStyle: { backgroundColor: colors.canvas },
    }}>
      {user ? (
        <>
          <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'By the Book' }} />
          <Stack.Screen name="Properties" component={PropertiesScreen} options={{ title: 'Properties' }} />
          <Stack.Screen name="Account" component={AccountScreen} options={{ title: 'Account' }} />
          <Stack.Screen name="Tenancy" component={TenancyScreen} options={{ title: 'Tenancy' }} />
          <Stack.Screen name="Inspection" component={InspectionScreen} options={{ title: 'Inspection' }} />
        </>
      ) : (
        <>
          <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Register" component={RegisterScreen} options={{ title: 'Create account' }} />
        </>
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer theme={theme}>
          <StatusBar style="dark" />
          <Routes />
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
