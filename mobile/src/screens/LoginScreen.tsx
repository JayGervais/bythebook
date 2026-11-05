import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useAuth } from '../auth';
import { RootParamList } from '../navigation';
import { Button, colors, ErrorText, Field } from '../ui';

export function LoginScreen({ navigation }: NativeStackScreenProps<RootParamList, 'Login'>) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function submit() {
    setError('');
    try {
      await signIn(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.');
    }
  }

  return (
    <View style={styles.page}>
      <Image source={require('../../assets/icon.png')} style={styles.mark} accessibilityLabel="By the Book" />
      <Text style={styles.kicker}>Alberta rental management</Text>
      <Text style={styles.title}>By the Book</Text>
      <Text style={styles.lede}>Inspection reports, deposits, rent, and notices for rental properties.</Text>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <Field label="Email" value={email} onChangeText={setEmail} keyboard="email-address" />
      <Field label="Password" value={password} onChangeText={setPassword} secure />
      <Button label="Sign in" onPress={() => void submit()} />
      <Pressable accessibilityRole="link" onPress={() => navigation.navigate('Register')}>
        <Text style={styles.link}>Create an account</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.canvas, padding: 24, gap: 14, justifyContent: 'center' },
  mark: { width: 72, height: 72, borderRadius: 0 },
  kicker: { color: colors.brandStrong, fontSize: 12, letterSpacing: 1.4, textTransform: 'uppercase', fontWeight: '600' },
  title: { fontSize: 34, fontWeight: '700', color: colors.ink, letterSpacing: -0.5 },
  lede: { color: colors.muted, fontSize: 16, lineHeight: 23 },
  link: { color: colors.accent, fontSize: 15, fontWeight: '600' },
});
