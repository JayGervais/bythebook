import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

export const colors = {
  canvas: '#f4f5f7',
  card: '#ffffff',
  ink: '#12141a',
  muted: '#667085',
  line: '#e6e8ee',
  accent: '#0f8f5b',
  accentDeep: '#0c6b44',
  accentSoft: '#ecfdf3',
  amber: '#b45309',
  amberSoft: '#fffaeb',
  tide: '#0e7490',
  tideSoft: '#ecfeff',
  danger: '#b42318',
  dangerBg: '#fef3f2',
};

export function Screen({ children }: { children: React.ReactNode }) {
  return <View style={styles.screen}>{children}</View>;
}

export function Field({
  label, value, onChangeText, secure, placeholder, keyboard,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  secure?: boolean;
  placeholder?: string;
  keyboard?: 'default' | 'email-address' | 'numeric' | 'decimal-pad';
}) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        secureTextEntry={secure}
        placeholder={placeholder}
        placeholderTextColor="#98a2b3"
        autoCapitalize={keyboard === 'email-address' ? 'none' : 'sentences'}
        keyboardType={keyboard || 'default'}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={[styles.input, focused && styles.inputFocused]}
      />
    </View>
  );
}

export function Button({ label, onPress, secondary }: { label: string; onPress: () => void; secondary?: boolean }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={[styles.button, secondary && styles.secondary]}>
      <Text style={[styles.buttonText, secondary && styles.secondaryText]}>{label}</Text>
    </Pressable>
  );
}

export function Card({ children }: { children: React.ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

export function ErrorText({ children }: { children: string }) {
  return <Text style={styles.error}>{children}</Text>;
}

const shadow = {
  shadowColor: '#12141a',
  shadowOpacity: 0.05,
  shadowRadius: 16,
  shadowOffset: { width: 0, height: 8 },
  elevation: 2,
};

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.canvas },
  field: { gap: 6 },
  label: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  input: {
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.card,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.ink,
  },
  inputFocused: { borderColor: colors.accent, borderWidth: 1.5 },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 10,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  secondary: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line },
  buttonText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  secondaryText: { color: colors.ink },
  card: {
    backgroundColor: colors.card,
    borderRadius: 18,
    padding: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: colors.line,
    ...shadow,
  },
  error: { backgroundColor: colors.dangerBg, color: colors.danger, padding: 12, borderRadius: 12 },
});
