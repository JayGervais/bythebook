import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

export const colors = {
  canvas: '#f5f5f7',
  card: '#ffffff',
  ink: '#1d1d1f',
  muted: '#6e6e73',
  line: '#d2d2d7',
  accent: '#3e6b5a',
  accentDeep: '#345c4d',
  accentSoft: 'rgba(62, 107, 90, 0.10)',
  brand: '#7a6e62',
  brandStrong: '#65594f',
  brandSoft: 'rgba(122, 110, 98, 0.14)',
  amber: '#8f5e45',
  amberSoft: 'rgba(143, 94, 69, 0.12)',
  tide: '#4d6570',
  tideSoft: 'rgba(77, 101, 112, 0.12)',
  danger: '#b3261e',
  dangerBg: 'rgba(179, 38, 30, 0.06)',
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
  shadowColor: '#7a6e62',
  shadowOpacity: 0.18,
  shadowRadius: 16,
  shadowOffset: { width: 0, height: 6 },
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
    borderRadius: 980,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  secondary: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line },
  buttonText: { color: '#fff', fontSize: 15, fontWeight: '500' },
  secondaryText: { color: colors.ink },
  card: {
    backgroundColor: colors.card,
    borderRadius: 0,
    padding: 16,
    gap: 8,
    ...shadow,
  },
  error: { backgroundColor: colors.dangerBg, color: colors.danger, padding: 12, borderRadius: 12 },
});
