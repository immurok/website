#!/usr/bin/env python3
"""Generate the per-language FAQ pages under website/<lang>/index.html.

A third of our search impressions now come from AI assistants, and a large
share of those queries are in languages other than English: price, where to
buy, which countries we ship to, does it work on Linux. Browser translation
does not help there, because the crawler reads the source HTML. So each
language gets a real page with real text.

The pages are deliberately small and static: the same fifteen answers as the
English homepage's "Straight answers" section, the site's own CSS, hreflang
alternates in every direction, and a link back to the full English site.

Usage:
    python3 tools/build-lang-pages.py          # writes website/<lang>/index.html
    python3 tools/build-lang-pages.py --check   # exit 1 if anything is stale
"""

import argparse
import html
import json
import os
import sys

SITE = "https://immurok.com"
BUY = SITE + "/#pricing"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ── Translations ────────────────────────────────────────────────────────────
# Order of the fifteen answers is identical in every language and matches the
# English homepage. Keep it that way: the hreflang cluster is only useful if
# the pages are genuine equivalents.

LANGS = {
"ja": {
 "og": "ja_JP",
 "name": "日本語",
 "title": "immurok の価格・購入方法・対応OS｜Mac / Windows / Linux 用ワイヤレス指紋キー",
 "desc": "immurok の価格（US$69）、購入方法、発送国、対応OS、セキュリティ、サブスクの有無、リセット方法をまとめました。",
 "lead": "immurok についてよく聞かれる質問と、その答えです。英語版のサイトと同じ内容を日本語で書いています。",
 "cta": "今すぐ購入 · US$69",
 "back": "英語版のサイト全体を見る",
 "qa": [
  ("どのパソコンと OS に対応していますか",
   "macOS 13.0 以降、Windows 10 と 11、そして主要な Linux ディストリビューションに対応しています。Mac 版は Apple Silicon と Intel 共通のユニバーサルビルドです。Windows 版は x64 と Arm64 のネイティブインストーラーがあり、Credential Provider として統合されるのでロック画面でも使えます。Linux 版は Rust 製のデーモンで、PAM と polkit に統合されます。Ubuntu、Fedora、Arch、Debian でテストしており、他の多くのディストリビューションでもビルドできます。本体がパソコンとは別の Bluetooth 機器なので、Mac mini でも Mac Studio でも iMac でも、閉じた MacBook でも外付けキーボードでも Windows デスクトップでも、同じように使えます。1 台のキーを 2 台のパソコンに登録し、専用の指で切り替えることもできます。"),
  ("Windows Hello に対応していますか",
   "Windows Hello 対応デバイスではありませんが、その必要もありません。Windows Hello はノートパソコン内蔵のセンサーや認定済みのキーボード・ウェブカメラのための Microsoft の仕組みです。immurok は別の経路でサインインします。Windows のサインイン画面の中で動く Credential Provider を使うので、指を触れるだけで Hello のセンサーと同じようにロック画面を解除でき、Hello センサーのないデスクトップ PC や外付けキーボードでも使えます。しかも Hello より先まで行きます。同じ一回のタッチで SSH と Git のコミットに署名し、1Password と Bitwarden を解除し、TOTP コードを取り出せます。同じキーが macOS と Linux でも使えます。"),
  ("パスキーや FIDO に対応していますか",
   "いいえ。immurok は FIDO デバイスではありません。ウェブサイトにパスキーやセキュリティキーとして登録することはできず、YubiKey の代わりにもなりません。immurok が担うのはその一段下、目の前のパソコンの層です。画面ロックの解除、sudo や管理者パスワードの承認、SSH と Git の署名、パスワードマネージャーの解除、TOTP コードの取り出し。ウェブサイトへのサインインにはパスキーやセキュリティキーをそのまま使ってください。残りは immurok が受け持ちます。私たちの多くも両方を使っています。"),
  ("ChromeOS に対応していますか",
   "いいえ。ChromeOS はサードパーティのソフトウェアが画面ロック解除やシステム認証に関わる手段を用意していないため、immurok が入り込む場所がありません。対応しているのは macOS 13 以降、Windows 10 と 11、主要な Linux ディストリビューションです。"),
  ("1 つのキーを複数のパソコンで使えますか",
   "はい、最大 2 台まで、ただし接続できるのは同時に 1 台です。キーは独立したペアリングを 2 つ持ち、それぞれに固有の鍵があるので、2 台とも結び付いたままですが、通信するのは常にどちらか 1 台だけです。指を 1 本「切り替え用」として登録しておき、その指を触れるとキーが一方のパソコンからもう一方へ移り、移った先のパソコンが自動で再接続します。片方のパソコンを解除しても、消えるのはそのペアリングだけで、もう一方のパソコンと登録済みの指紋はそのまま残ります。"),
  ("1Password、Bitwarden、LastPass、Proton Pass を解除できますか",
   "はい、4 つとも macOS、Windows、Linux で対応しています。パスワードマネージャーが解除画面を出したとき、指を触れるとキーに保存された専用のパスワードが入力され、送信されます。このパスワードはログインパスワードとは別に保存され、有効・無効も別々に切り替えられます。受け取れるのは署名済みの許可リストに載ったアプリだけです。"),
  ("USB で接続できますか",
   "充電にだけ使えます。USB-C ポートはバッテリーを充電するためのもので、データは流れません。ペアリング、指紋の判定結果、その他すべて Bluetooth LE で通信するので、パソコン側に Bluetooth が必要で、使用中にポートを空けておく必要はありません。"),
  ("バッテリーは交換できますか",
   "はい。キーは充電式の 110 mAh リチウム電池で動き、USB-C で充電して、通常の使い方なら 1 回の充電で 1 か月以上持ちます。特注品ではなく標準規格のサイズなので、自分で交換できます。先にペアリングを解除するか工場出荷状態にリセットしてください。ペアリング済みのキーのケースを開けると、防タンパースイッチが作動してデータが消去されます。電池を入れ替え、ケースを閉じて、もう一度ペアリングしてください。"),
  ("セキュリティはどうなっていますか。指紋データはどこに保存されますか",
   "指紋データは本体の中にだけ保存され、照合も本体の中で行われます。パソコンのディスク、ネットワーク、クラウドには一切届きません。Bluetooth を通るのは HMAC で署名された「照合に成功した」という通知だけで、指紋そのものは流れません。ペアリングは本体とパソコンの間の ECDH 鍵交換です。ファームウェアの更新は署名を検証してから適用されます。アカウントもサーバーもテレメトリもないので、オフラインで完結し、私たちがいなくなっても動き続けます。"),
  ("オープンソースですか",
   "ソースコードはすべて GitHub で公開しています。ライセンスは二つに分かれます。macOS / Windows / Linux のアプリは、PAM モジュールと Windows の Credential Provider を含めて Apache 2.0 のオープンソースです。ファームウェアとハードウェアは BSL 1.1 のソース公開ライセンスで、2030 年に Apache 2.0 に切り替わります。中身をすべて読み、修正し、自分でビルドして書き込むことができます。切り替えまで留保しているのは、競合するハードウェアを販売する権利だけです。"),
  ("自分でファームウェアをビルドして書き込めますか",
   "はい。ファームウェアとハードウェアのソースは公開されており、基板には書き込み用のインターフェースがあるので、自分でファームウェアをビルドして書き込めます。開ける前にキーをリセットしてください。ペアリング済みのキーを開けると防タンパースイッチが作動します。自分でビルドしたファームウェアを書き込んだ個体は保証の対象外となり、公式のファームウェア更新も受けられなくなります。"),
  ("YubiKey やパスワードマネージャー、Touch ID とは何が違いますか",
   "レイヤーが違うので、併用できます。YubiKey やパスキーは「Web サイトに対して本人であることを証明する」ものです。immurok は「目の前のパソコンでパスワードを打つ手間をなくす」ものです。画面ロックの解除、sudo、管理者承認、SSH と Git の署名がそれにあたります。パスワードマネージャーはパスワードを保管するものですが、immurok は macOS・Windows・Linux で 1Password や Bitwarden のロックを指一本で解除でき、TOTP のシードを本体に保存できるので、二要素認証の種をパソコン上のアプリに置かずに済みます。Touch ID は Apple 自身のセンサーで、Secure Enclave と一体化していて他社は利用できず、そもそも Mac mini や外付けキーボードには存在しません。immurok は独立した機器で、sudo と管理者承認は PAM という OS 本来の仕組みを通り、画面ロック解除は別途文書化された経路を使います。"),
  ("Mac 用の単体の Touch ID はありますか",
   "Apple からは出ていません。Touch ID は MacBook に内蔵されているものと、Touch ID 搭載 Magic Keyboard（US$149〜199、Apple Silicon の Mac が必要）だけで、センサーはキーボードと一体です。単体の Touch ID センサーは存在せず、Touch ID は Secure Enclave と一体化しているため、他社が作ることもできません。immurok はそれに最も近い製品です。机の上に置く単体のワイヤレス指紋キーで、今使っているキーボードの横に置くだけで使えます。Mac mini、Mac Studio、iMac、閉じたままの MacBook で、画面ロックの解除、sudo と管理者承認、1Password と Bitwarden のロック解除、SSH と Git のコミット署名ができます。Touch ID ではありませんし、そう名乗るつもりもありません。独自のセンサーと独自のセキュリティモデルを持つ別の機器で、Windows と Linux でも使えます。"),
  ("サブスクリプションは必要ですか",
   "必要ありません。サブスクリプションもアカウントもクラウドサービスもありません。本体を一度買うだけです。macOS / Windows / Linux のアプリもファームウェア更新も無料です。インターネットに一度もつながなくても、何ひとつ止まりません。"),
  ("リセットの方法は。紛失したらどうなりますか",
   "ボタンを約 10 秒間押し続けると工場出荷状態に戻ります。ペアリング鍵、登録済みの指紋、保存された認証情報がすべて消去され、再ペアリングできる状態で再起動します。この操作は取り消せません。完全な初期化をせずに別のパソコンへ移したい場合は、アプリの「ペアリング解除（Unpair）」を使ってください。紛失しても指紋を取り出されることはありません。テンプレートは本体から外に出ず、ケースをこじ開けると改ざん検知スイッチが働いてすべてのデータを消去し、ランプが赤の点灯のまま停止します。製品には 1 年間の保証が付きます。サポート窓口の連絡先は取扱説明書とアプリに記載しています。"),
 ]},

"es": {
 "og": "es_ES",
 "name": "Español",
 "title": "immurok: precio, dónde comprarlo y compatibilidad | Llave de huella inalámbrica para Mac, Windows y Linux",
 "desc": "Precio de immurok (US$69), dónde comprarlo, a qué países enviamos, sistemas compatibles, seguridad, suscripción y cómo restablecerlo.",
 "lead": "Las preguntas que más nos hacen sobre immurok, respondidas. Es el mismo contenido que la web en inglés.",
 "cta": "Comprar ahora · US$69",
 "back": "Ver el sitio completo en inglés",
 "qa": [
  ("¿Con qué ordenadores y sistemas operativos funciona?",
   "macOS 13.0 o posterior, Windows 10 y 11, y la mayoría de distribuciones de Linux. La app de Mac es una única compilación universal para Apple Silicon e Intel. Windows tiene instaladores nativos x64 y Arm64 y se integra como Credential Provider, así que funciona en la pantalla de bloqueo. Linux es un demonio en Rust con integración PAM y polkit, probado en Ubuntu, Fedora, Arch y Debian, y compila en casi cualquier otra distribución. Como la llave es un dispositivo Bluetooth independiente y no un sensor incrustado en un portátil, funciona igual en un Mac mini, un Mac Studio, un iMac, un MacBook cerrado, un teclado externo o un PC de sobremesa. Una misma llave puede quedar vinculada a dos ordenadores a la vez y cambiar entre ellos con una huella dedicada."),
  ("¿Funciona con Windows Hello?",
   "No es un dispositivo Windows Hello, y no necesita serlo. Windows Hello es el marco de Microsoft para sensores integrados en un portátil o en un teclado o cámara certificados. immurok inicia sesión por otra vía: un Credential Provider que corre dentro de la pantalla de inicio de sesión de Windows, así que un toque desbloquea la pantalla exactamente como lo haría un sensor Hello, en cualquier PC de sobremesa o teclado externo donde no hay sensor Hello. Y va más allá de Hello. El mismo toque firma commits de SSH y Git, desbloquea 1Password y Bitwarden y entrega códigos TOTP, y la misma llave funciona también en macOS y Linux."),
  ("¿Es compatible con passkeys o FIDO?",
   "No. immurok no es un dispositivo FIDO. No se registra en sitios web como passkey ni como llave de seguridad, y no sustituye a una YubiKey. Trabaja una capa más abajo, en la máquina que tienes delante: desbloqueo de pantalla, avisos de sudo y de administrador, firma de SSH y Git, desbloqueo del gestor de contraseñas y códigos TOTP. Sigue usando tus passkeys o tu llave de seguridad para entrar en sitios web; immurok se ocupa del resto, y muchos de nosotros usamos ambas cosas."),
  ("¿Es compatible con ChromeOS?",
   "No. ChromeOS no da al software de terceros ninguna forma de participar en el desbloqueo de pantalla ni en la autenticación del sistema, así que immurok no tiene dónde engancharse. Funciona con macOS 13 o posterior, Windows 10 y 11 y la mayoría de distribuciones Linux."),
  ("¿Puedo usar una llave con más de un ordenador?",
   "Sí, con hasta dos ordenadores, conectada a uno cada vez. La llave guarda dos emparejamientos independientes, cada uno con sus propias claves, así que las dos máquinas siguen vinculadas, pero solo habla con una de ellas en cada momento. Registras un dedo como dedo de cambio. Al tocarlo, la llave pasa de un ordenador al otro, y el ordenador de destino se reconecta solo. Quitar un ordenador borra solo ese emparejamiento; el otro ordenador y tus huellas registradas quedan intactos."),
  ("¿Desbloquea 1Password, Bitwarden, LastPass o Proton Pass?",
   "Sí, los cuatro, en macOS, Windows y Linux. Cuando el gestor muestra su pantalla de desbloqueo, un toque rellena una contraseña dedicada que vive en la llave, guardada aparte de tu contraseña de inicio de sesión y activada por separado, y la envía. Solo la reciben las aplicaciones de una lista blanca firmada."),
  ("¿Puedo conectarla por USB?",
   "Solo para cargarla. El puerto USB-C carga la batería y no transporta datos. El emparejamiento, los resultados de huella y todo lo demás van por Bluetooth LE, así que tu ordenador necesita Bluetooth y la llave no ocupa ningún puerto mientras trabajas."),
  ("¿Se puede cambiar la batería?",
   "Sí. La llave funciona con una celda de litio recargable de 110 mAh que se carga por USB-C y dura más de un mes de uso normal por carga. Es un tamaño estándar, no una pieza a medida, y puedes cambiarla tú mismo. Antes, desempareja la llave o restáurala de fábrica: abrir la carcasa de una llave emparejada activa el interruptor antimanipulación y la borra. Cambia la celda, cierra la carcasa y vuelve a emparejar."),
  ("¿Qué nivel de seguridad tiene? ¿Dónde se guardan mis huellas?",
   "En el dispositivo, y en ningún otro sitio. Las plantillas de huella se guardan y se comparan dentro de la propia llave. Nunca llegan al disco de tu ordenador, ni a la red, ni a ningún servicio en la nube. Por Bluetooth solo viaja una notificación firmada con HMAC que dice que la huella coincide, nunca la huella. El emparejamiento es un intercambio ECDH directo entre el dispositivo y tu máquina. Las actualizaciones de firmware van firmadas y se verifican antes de instalarse. No hay cuenta, ni servidor, ni telemetría: todo funciona sin conexión y seguiría funcionando si nosotros desapareciéramos."),
  ("¿Es de código abierto?",
   "Todo el código fuente es público en GitHub, con dos licencias distintas. Las apps de macOS, Windows y Linux, incluidos los módulos PAM y el Credential Provider de Windows, son código abierto bajo Apache 2.0. El firmware y el hardware son de código disponible bajo BSL 1.1 y pasan a Apache 2.0 en 2030. Puedes leerlo todo, modificarlo, compilarlo y grabarlo en tu propia unidad. El único derecho que nos reservamos hasta la conversión es vender hardware competidor."),
  ("¿Puedo compilar y grabar mi propio firmware?",
   "Sí. El código del firmware y del hardware es público, y la placa expone una interfaz de programación para que compiles tu propio firmware y lo grabes. Restaura la llave antes de abrirla, porque abrir una llave emparejada activa el interruptor antimanipulación. Una vez que una unidad ejecuta firmware compilado por ti, queda fuera de garantía y deja de recibir actualizaciones oficiales de firmware."),
  ("¿En qué se diferencia de una YubiKey, un gestor de contraseñas o Touch ID?",
   "Son capas distintas y se complementan. Una YubiKey y las passkeys demuestran quién eres ante una web. immurok elimina la fricción de la contraseña en la máquina que tienes delante: desbloqueo de pantalla, sudo, peticiones de administrador, firma de SSH y Git. Un gestor de contraseñas guarda tus contraseñas; immurok desbloquea 1Password y Bitwarden con un toque en macOS, Windows y Linux, y guarda las semillas TOTP en el propio dispositivo, para que tus códigos de doble factor no vivan en una app del escritorio. Touch ID es el sensor propio de Apple, fundido con el Secure Enclave, cerrado a terceros, y sencillamente no existe en un Mac mini ni en un teclado externo. immurok es un dispositivo independiente: sudo y las peticiones de administrador pasan por PAM, un mecanismo real del sistema, y el desbloqueo de pantalla usa una ruta auxiliar documentada aparte."),
  ("¿Existe un Touch ID independiente para el Mac?",
   "De Apple, no. Touch ID solo viene integrado en los MacBook y en el Magic Keyboard con Touch ID, que cuesta entre US$149 y US$199, exige un Mac con Apple Silicon y ata el sensor a un teclado que quizá no quieras. No existe un sensor Touch ID suelto, y como Touch ID está fundido con el Secure Enclave, un tercero tampoco puede fabricarlo. immurok es lo más parecido: una llave de huella inalámbrica independiente que se queda en tu escritorio junto al teclado que ya usas. En un Mac mini, Mac Studio, iMac o MacBook cerrado desbloquea la pantalla, aprueba sudo y las peticiones de administrador, desbloquea 1Password y Bitwarden y firma commits de SSH y Git. No es Touch ID ni pretende serlo: es un dispositivo aparte, con su propio sensor y su propio modelo de seguridad, y además funciona en Windows y Linux."),
  ("¿Hace falta una suscripción?",
   "No. Ni suscripción, ni cuenta, ni servicio en la nube. Pagas una vez por el dispositivo. Las apps de macOS, Windows y Linux son gratuitas, y las actualizaciones de firmware también. Nada deja de funcionar aunque no conectes nunca el dispositivo a internet, porque no lo necesita."),
  ("¿Cómo se restablece? ¿Y si lo pierdo?",
   "Mantén pulsado el botón unos diez segundos para restablecerlo de fábrica. El dispositivo borra todo: claves de emparejamiento, todas las huellas registradas y las credenciales guardadas, y se reinicia listo para emparejarse otra vez. No se puede deshacer. Para pasar la llave a otro ordenador sin un borrado completo, usa Desemparejar en la app. Si la pierdes, nadie puede extraer tus huellas: las plantillas nunca salen del hardware y forzar la carcasa activa un interruptor antimanipulación que lo borra todo y deja la luz en rojo fijo. Cada unidad incluye un año de garantía. La dirección de soporte viene en el manual de usuario y aparece en la app."),
 ]},

"pt": {
 "og": "pt_BR",
 "name": "Português",
 "title": "immurok: preço, onde comprar e compatibilidade | Chave de impressão digital sem fio para Mac, Windows e Linux",
 "desc": "Preço do immurok (US$69), onde comprar, para quais países enviamos, sistemas compatíveis, segurança, assinatura e como redefinir.",
 "lead": "As perguntas que mais recebemos sobre o immurok, respondidas. É o mesmo conteúdo do site em inglês.",
 "cta": "Comprar agora · US$69",
 "back": "Ver o site completo em inglês",
 "qa": [
  ("Com quais computadores e sistemas operacionais funciona?",
   "macOS 13.0 ou mais recente, Windows 10 e 11, e a maioria das distribuições Linux. O app do Mac é uma única build universal para Apple Silicon e Intel. O Windows tem instaladores nativos x64 e Arm64 e se integra como Credential Provider, então funciona na tela de bloqueio. O Linux é um daemon em Rust com integração PAM e polkit, testado em Ubuntu, Fedora, Arch e Debian, e compila na maioria das outras distribuições. Como a chave é um dispositivo Bluetooth separado, e não um sensor embutido no notebook, ela funciona igual em um Mac mini, um Mac Studio, um iMac, um MacBook fechado, um teclado externo ou um PC de mesa. Uma mesma chave pode ficar vinculada a dois computadores ao mesmo tempo e alternar entre eles com uma digital dedicada."),
  ("Funciona com o Windows Hello?",
   "Não é um dispositivo Windows Hello, e não precisa ser. O Windows Hello é a estrutura da Microsoft para sensores embutidos em um notebook ou em um teclado ou webcam certificados. O immurok faz o login por outro caminho: um Credential Provider que roda dentro da tela de login do Windows, então um toque destrava a tela exatamente como um sensor Hello faria, em qualquer PC de mesa ou teclado externo onde não existe sensor Hello. E vai além do Hello. O mesmo toque assina commits de SSH e Git, destrava o 1Password e o Bitwarden e libera códigos TOTP, e a mesma chave também funciona no macOS e no Linux."),
  ("É compatível com passkeys ou FIDO?",
   "Não. O immurok não é um dispositivo FIDO. Ele não se registra em sites como passkey nem como chave de segurança, e não substitui uma YubiKey. Ele trabalha uma camada abaixo, na máquina à sua frente: desbloqueio de tela, avisos de sudo e de administrador, assinatura de SSH e Git, desbloqueio do gerenciador de senhas e códigos TOTP. Continue usando suas passkeys ou sua chave de segurança para entrar em sites; o immurok cuida do resto, e muitos de nós usamos os dois."),
  ("É compatível com ChromeOS?",
   "Não. O ChromeOS não dá a software de terceiros nenhuma forma de participar do desbloqueio de tela ou da autenticação do sistema, então não há onde o immurok se encaixar. Ele funciona com macOS 13 ou mais recente, Windows 10 e 11 e a maioria das distribuições Linux."),
  ("Posso usar uma chave com mais de um computador?",
   "Sim, com até dois computadores, conectada a um de cada vez. A chave guarda dois pareamentos independentes, cada um com suas próprias chaves, então as duas máquinas continuam vinculadas, mas ela só conversa com uma delas de cada vez. Você cadastra um dedo como dedo de troca. Ao tocá-lo, a chave passa de um computador para o outro, e o computador de destino reconecta sozinho. Remover um computador apaga só aquele pareamento; o outro computador e suas digitais cadastradas ficam intactos."),
  ("Destrava 1Password, Bitwarden, LastPass ou Proton Pass?",
   "Sim, os quatro, no macOS, no Windows e no Linux. Quando o gerenciador mostra a tela de desbloqueio, um toque preenche uma senha dedicada que fica na chave, guardada separadamente da sua senha de login e ativada separadamente, e a envia. Só aplicativos de uma lista de permissões assinada a recebem."),
  ("Posso conectar por USB?",
   "Só para carregar. A porta USB-C carrega a bateria e não transporta dados. O pareamento, os resultados de digital e todo o resto vão por Bluetooth LE, então seu computador precisa de Bluetooth e a chave não ocupa nenhuma porta enquanto você trabalha."),
  ("A bateria pode ser trocada?",
   "Sim. A chave funciona com uma célula de lítio recarregável de 110 mAh que carrega por USB-C e dura mais de um mês de uso normal por carga. É um tamanho padrão de mercado, não uma peça sob medida, e você mesmo pode trocá-la. Antes, despareie a chave ou restaure os padrões de fábrica: abrir a carcaça de uma chave pareada aciona a chave antiviolação e apaga tudo. Troque a célula, feche a carcaça e pareie de novo."),
  ("Qual é o nível de segurança? Onde ficam minhas digitais?",
   "No dispositivo, e em nenhum outro lugar. Os templates de digital são armazenados e comparados dentro da própria chave. Eles nunca chegam ao disco do seu computador, à rede ou a qualquer serviço em nuvem. Pelo Bluetooth trafega apenas uma notificação assinada com HMAC dizendo que a digital bateu, nunca a digital em si. O pareamento é uma troca ECDH direta entre o dispositivo e a sua máquina. As atualizações de firmware são assinadas e verificadas antes de serem instaladas. Não há conta, servidor nem telemetria: tudo funciona offline e continuaria funcionando se nós desaparecêssemos."),
  ("É código aberto?",
   "Todo o código-fonte é público no GitHub, sob duas licenças diferentes. Os apps de macOS, Windows e Linux, incluindo os módulos PAM e o Credential Provider do Windows, são código aberto sob Apache 2.0. O firmware e o hardware são de código disponível sob BSL 1.1 e passam para Apache 2.0 em 2030. Você pode ler tudo, modificar, compilar e gravar na sua própria unidade. O único direito reservado até a conversão é vender hardware concorrente."),
  ("Posso compilar e gravar meu próprio firmware?",
   "Sim. O código do firmware e do hardware é público, e a placa expõe uma interface de programação para você compilar seu próprio firmware e gravá-lo. Restaure a chave antes de abri-la, porque abrir uma chave pareada aciona a chave antiviolação. Depois que uma unidade roda firmware compilado por você, ela sai da garantia e deixa de receber atualizações oficiais de firmware."),
  ("Qual a diferença para uma YubiKey, um gerenciador de senhas ou o Touch ID?",
   "São camadas diferentes e funcionam juntas. Uma YubiKey e as passkeys provam quem você é para um site. O immurok tira o atrito da senha na máquina à sua frente: desbloqueio de tela, sudo, pedidos de administrador, assinatura de SSH e Git. Um gerenciador de senhas guarda suas senhas; o immurok destrava o 1Password e o Bitwarden com um toque no macOS, no Windows e no Linux, e guarda as sementes TOTP no próprio dispositivo, para que seus códigos de dois fatores não fiquem em um app do desktop. O Touch ID é o sensor da própria Apple, fundido ao Secure Enclave, fechado para terceiros, e simplesmente não existe em um Mac mini ou em um teclado externo. O immurok é um dispositivo independente: sudo e pedidos de administrador passam pelo PAM, um mecanismo real do sistema, e o desbloqueio de tela usa um caminho auxiliar documentado à parte."),
  ("Existe um Touch ID avulso para o Mac?",
   "Da Apple, não. O Touch ID só vem embutido nos MacBook e no Magic Keyboard com Touch ID, que custa de US$149 a US$199, exige um Mac com Apple Silicon e prende o sensor a um teclado que talvez você nem queira. Não existe um sensor Touch ID avulso, e como o Touch ID é fundido ao Secure Enclave, terceiros também não podem fabricar um. O immurok é o que chega mais perto: uma chave de impressão digital sem fio, independente, que fica na sua mesa ao lado do teclado que você já usa. Em um Mac mini, Mac Studio, iMac ou MacBook fechado ele desbloqueia a tela, aprova sudo e pedidos de administrador, destrava o 1Password e o Bitwarden e assina commits de SSH e Git. Não é Touch ID e não finge ser: é um dispositivo à parte, com sensor próprio e modelo de segurança próprio, e ainda funciona no Windows e no Linux."),
  ("Precisa de assinatura?",
   "Não. Sem assinatura, sem conta, sem serviço em nuvem. Você paga uma vez pelo dispositivo. Os apps de macOS, Windows e Linux são gratuitos, e as atualizações de firmware também. Nada para de funcionar se você nunca conectar o dispositivo à internet, porque ele não precisa disso."),
  ("Como redefinir? E se eu perder?",
   "Segure o botão por cerca de dez segundos para restaurar de fábrica. O dispositivo apaga tudo: chaves de pareamento, todas as digitais cadastradas e as credenciais armazenadas, e reinicia pronto para parear de novo. Isso não pode ser desfeito. Para passar a chave para outro computador sem apagar tudo, use Desparear no app. Se você perder, ninguém consegue extrair suas digitais: os templates nunca saem do hardware, e forçar a carcaça aciona uma chave antiviolação que apaga tudo e deixa a luz em vermelho fixo. Cada unidade inclui um ano de garantia. O endereço de suporte está no manual do usuário e aparece no app."),
 ]},

"de": {
 "og": "de_DE",
 "name": "Deutsch",
 "title": "immurok: Preis, Kauf und Kompatibilität | Kabelloser Fingerabdruck-Key für Mac, Windows und Linux",
 "desc": "immurok Preis (US$69), wo man ihn kauft, Versandländer, unterstützte Systeme, Sicherheit, Abo und Zurücksetzen.",
 "lead": "Die Fragen, die uns am häufigsten zu immurok gestellt werden, hier beantwortet. Inhaltlich dasselbe wie auf der englischen Seite.",
 "cta": "Jetzt kaufen · US$69",
 "back": "Die vollständige Seite auf Englisch ansehen",
 "qa": [
  ("Mit welchen Rechnern und Betriebssystemen funktioniert er?",
   "macOS 13.0 oder neuer, Windows 10 und 11 sowie die meisten Linux-Distributionen. Die Mac-App ist ein einziges Universal-Build für Apple Silicon und Intel. Für Windows gibt es native x64- und Arm64-Installer, und die Integration läuft über einen Credential Provider, funktioniert also auf dem Sperrbildschirm. Linux ist ein Rust-Daemon mit PAM- und polkit-Integration, getestet auf Ubuntu, Fedora, Arch und Debian, und er baut auf den meisten anderen Distributionen. Weil der Key ein eigenständiges Bluetooth-Gerät ist und kein im Laptop verbauter Sensor, funktioniert er auf einem Mac mini, einem Mac Studio, einem iMac, einem zugeklappten MacBook, einer externen Tastatur oder einem Desktop-PC gleich gut. Ein Key kann gleichzeitig an zwei Rechner gebunden sein; mit einem eigens dafür angelernten Finger wechselt man zwischen ihnen."),
  ("Funktioniert es mit Windows Hello?",
   "Es ist kein Windows-Hello-Gerät, und das muss es auch nicht sein. Windows Hello ist Microsofts Rahmen für Sensoren, die in ein Notebook oder eine zertifizierte Tastatur oder Webcam eingebaut sind. immurok meldet dich auf einem anderen Weg an: über einen Credential Provider, der im Windows-Anmeldebildschirm läuft. Eine Berührung entsperrt den Sperrbildschirm also genau wie ein Hello-Sensor, an jedem Desktop-PC und jeder externen Tastatur, wo es keinen Hello-Sensor gibt. Und es geht über Hello hinaus. Dieselbe Berührung signiert SSH- und Git-Commits, entsperrt 1Password und Bitwarden und gibt TOTP-Codes frei, und derselbe Schlüssel funktioniert auch unter macOS und Linux."),
  ("Unterstützt es Passkeys oder FIDO?",
   "Nein. immurok ist kein FIDO-Gerät. Es registriert sich bei Websites weder als Passkey noch als Sicherheitsschlüssel, und es ersetzt keinen YubiKey. Es arbeitet eine Ebene tiefer, auf dem Rechner vor dir: Bildschirmentsperrung, sudo- und Admin-Abfragen, SSH- und Git-Signaturen, Entsperren des Passwortmanagers und TOTP-Codes. Behalte deine Passkeys oder deinen Sicherheitsschlüssel für die Anmeldung bei Websites; immurok übernimmt den Rest, und viele von uns benutzen beides."),
  ("Unterstützt es ChromeOS?",
   "Nein. ChromeOS gibt Software von Drittanbietern keine Möglichkeit, sich an der Bildschirmentsperrung oder der Systemauthentifizierung zu beteiligen, also gibt es für immurok nichts, wo es ansetzen könnte. Es funktioniert mit macOS 13 oder neuer, Windows 10 und 11 und den meisten Linux-Distributionen."),
  ("Kann ich einen Schlüssel mit mehr als einem Computer benutzen?",
   "Ja, mit bis zu zwei Computern, verbunden mit jeweils einem. Der Schlüssel hält zwei unabhängige Kopplungen, jede mit eigenen Schlüsseln, sodass beide Rechner gebunden bleiben, verbunden ist er aber immer nur mit einem. Du registrierst einen Finger als Wechselfinger. Berührst du ihn, wechselt der Schlüssel von einem Computer zum anderen, und der Zielcomputer verbindet sich von selbst neu. Entfernst du einen Computer, wird nur diese Kopplung gelöscht; der andere Computer und deine registrierten Fingerabdrücke bleiben unberührt."),
  ("Entsperrt es 1Password, Bitwarden, LastPass oder Proton Pass?",
   "Ja, alle vier, unter macOS, Windows und Linux. Zeigt der Manager seine Entsperrabfrage, trägt eine Berührung ein eigenes Passwort ein, das auf dem Schlüssel liegt, getrennt von deinem Anmeldepasswort gespeichert und getrennt einschaltbar, und schickt es ab. Nur Apps auf einer signierten Positivliste bekommen es je zu sehen."),
  ("Kann ich es per USB verbinden?",
   "Nur zum Laden. Der USB-C-Anschluss lädt den Akku und überträgt keine Daten. Kopplung, Fingerabdruck-Ergebnisse und alles andere laufen über Bluetooth LE. Dein Computer braucht also Bluetooth, und der Schlüssel belegt beim Arbeiten keinen Anschluss."),
  ("Ist der Akku austauschbar?",
   "Ja. Der Schlüssel läuft mit einer wiederaufladbaren 110-mAh-Lithiumzelle, die per USB-C geladen wird und bei normaler Nutzung mehr als einen Monat pro Ladung hält. Es ist eine handelsübliche Standardgröße, kein Sonderteil, und du kannst sie selbst tauschen. Entkopple den Schlüssel vorher oder setze ihn auf Werkseinstellungen zurück: Öffnest du das Gehäuse eines gekoppelten Schlüssels, löst der Manipulationsschalter aus und löscht ihn. Zelle tauschen, Gehäuse schließen, neu koppeln."),
  ("Wie sicher ist er? Wo liegen meine Fingerabdrücke?",
   "Auf dem Gerät, und sonst nirgends. Die Fingerabdruck-Templates werden auf dem Key selbst gespeichert und dort verglichen. Sie erreichen weder die Festplatte Ihres Rechners noch das Netzwerk noch irgendeinen Cloud-Dienst. Über Bluetooth geht nur eine HMAC-signierte Meldung, dass der Abdruck gepasst hat, niemals der Abdruck selbst. Das Pairing ist ein direkter ECDH-Austausch zwischen Gerät und Rechner. Firmware-Updates sind signiert und werden vor der Installation geprüft. Es gibt kein Konto, keinen Server und keine Telemetrie: alles läuft offline und würde weiterlaufen, wenn es uns nicht mehr gäbe."),
  ("Ist er Open Source?",
   "Der gesamte Quellcode ist auf GitHub öffentlich, unter zwei verschiedenen Lizenzen. Die Apps für macOS, Windows und Linux, einschließlich der PAM-Module und des Windows Credential Provider, sind Open Source unter Apache 2.0. Firmware und Hardware sind source-available unter BSL 1.1 und wechseln 2030 zu Apache 2.0. Sie können alles lesen, ändern, selbst bauen und auf Ihr eigenes Gerät flashen. Bis zur Umstellung behalten wir uns nur ein Recht vor: konkurrierende Hardware zu verkaufen."),
  ("Kann ich meine eigene Firmware bauen und aufspielen?",
   "Ja. Die Quellen von Firmware und Hardware sind öffentlich, und die Platine hat eine Programmierschnittstelle, über die du deine eigene Firmware bauen und aufspielen kannst. Setze den Schlüssel zurück, bevor du ihn öffnest, denn das Öffnen eines gekoppelten Schlüssels löst den Manipulationsschalter aus. Sobald ein Gerät selbst gebaute Firmware ausführt, erlischt die Garantie, und es erhält keine offiziellen Firmware-Updates mehr."),
  ("Worin unterscheidet er sich von einem YubiKey, einem Passwortmanager oder Touch ID?",
   "Andere Ebene, und sie ergänzen sich. Ein YubiKey und Passkeys weisen gegenüber einer Website nach, wer Sie sind. immurok nimmt die Passworthürde an dem Rechner weg, vor dem Sie sitzen: Bildschirm entsperren, sudo, Administratorabfragen, SSH- und Git-Signaturen. Ein Passwortmanager speichert Ihre Passwörter; immurok entsperrt 1Password und Bitwarden unter macOS, Windows und Linux mit einer Berührung und hält TOTP-Seeds auf dem Gerät, damit Ihre Zwei-Faktor-Geheimnisse nicht in einer Desktop-App liegen. Touch ID ist Apples eigener Sensor, fest mit der Secure Enclave verbunden, für Dritte verschlossen, und auf einem Mac mini oder einer externen Tastatur schlicht nicht vorhanden. immurok ist ein eigenständiges Gerät: sudo und Administratorabfragen laufen über PAM, einen echten Systemmechanismus, und das Entsperren des Bildschirms nutzt einen separat dokumentierten Hilfsweg."),
  ("Gibt es ein eigenständiges Touch ID für den Mac?",
   "Von Apple nicht. Touch ID gibt es nur fest eingebaut in MacBooks und im Magic Keyboard mit Touch ID, das US$149 bis US$199 kostet, einen Mac mit Apple Silicon voraussetzt und den Sensor an eine Tastatur bindet, die Sie vielleicht gar nicht wollen. Einen einzelnen Touch-ID-Sensor gibt es nicht, und weil Touch ID fest mit der Secure Enclave verbunden ist, kann ihn auch kein Dritter bauen. immurok kommt dem am nächsten: ein eigenständiger drahtloser Fingerabdruckschlüssel, der auf dem Schreibtisch neben der Tastatur liegt, die Sie schon benutzen. An einem Mac mini, Mac Studio, iMac oder zugeklappten MacBook entsperrt er den Bildschirm, bestätigt sudo und Administratorabfragen, entsperrt 1Password und Bitwarden und signiert SSH- und Git-Commits. Er ist kein Touch ID und gibt sich nicht als solches aus: ein separates Gerät mit eigenem Sensor und eigenem Sicherheitsmodell, das außerdem unter Windows und Linux funktioniert."),
  ("Brauche ich ein Abo?",
   "Nein. Kein Abo, kein Konto, kein Cloud-Dienst. Sie zahlen einmal für das Gerät. Die Apps für macOS, Windows und Linux sind kostenlos, Firmware-Updates ebenfalls. Nichts hört auf zu funktionieren, wenn Sie das Gerät nie mit dem Internet verbinden, denn das braucht es nicht."),
  ("Wie setze ich ihn zurück, und was ist, wenn ich ihn verliere?",
   "Halten Sie die Taste etwa zehn Sekunden gedrückt, um auf Werkseinstellungen zurückzusetzen. Das Gerät löscht alles: Pairing-Schlüssel, sämtliche angelernten Fingerabdrücke und gespeicherte Zugangsdaten, und startet bereit zum erneuten Koppeln. Das lässt sich nicht rückgängig machen. Um den Key ohne vollständiges Zurücksetzen an einen anderen Rechner zu geben, wählen Sie in der App Entkoppeln. Wenn Sie ihn verlieren, kann niemand Ihre Fingerabdrücke auslesen: die Templates verlassen die Hardware nie, und wer das Gehäuse aufbricht, löst einen Tamper-Schalter aus, der alles löscht und die Leuchte dauerhaft rot stehen lässt. Jedes Gerät hat ein Jahr Garantie. Die Support-Adresse steht im Handbuch und in der App."),
 ]},

"ko": {
 "og": "ko_KR",
 "name": "한국어",
 "title": "immurok 가격·구매·호환성 | Mac, Windows, Linux용 무선 지문 키",
 "desc": "immurok 가격(US$69), 구매 방법, 배송 국가, 지원 OS, 보안, 구독 여부, 초기화 방법을 정리했습니다.",
 "lead": "immurok에 대해 가장 많이 받는 질문과 답변입니다. 영문 사이트와 같은 내용입니다.",
 "cta": "지금 구매 · US$69",
 "back": "영문 사이트 전체 보기",
 "qa": [
  ("어떤 컴퓨터와 운영체제에서 쓸 수 있나요?",
   "macOS 13.0 이상, Windows 10과 11, 그리고 대부분의 Linux 배포판을 지원합니다. Mac 앱은 Apple Silicon과 Intel을 함께 지원하는 단일 유니버설 빌드입니다. Windows는 x64와 Arm64 네이티브 설치 파일을 제공하고 Credential Provider로 통합되므로 잠금 화면에서도 동작합니다. Linux는 Rust로 만든 데몬이며 PAM과 polkit에 통합됩니다. Ubuntu, Fedora, Arch, Debian에서 검증했고 다른 배포판에서도 대부분 빌드됩니다. 키가 노트북에 내장된 센서가 아니라 별도의 블루투스 기기이기 때문에 Mac mini, Mac Studio, iMac, 덮은 MacBook, 외장 키보드, 데스크톱 PC 모두 동일하게 동작합니다. 키 하나를 두 대의 컴퓨터에 동시에 등록해 두고 전용 지문으로 전환할 수도 있습니다."),
  ("Windows Hello를 지원하나요",
   "Windows Hello 기기는 아니지만, 그럴 필요도 없습니다. Windows Hello는 노트북에 내장된 센서나 인증받은 키보드·웹캠을 위한 Microsoft의 체계입니다. immurok은 다른 경로로 로그인합니다. Windows 로그인 화면 안에서 동작하는 Credential Provider를 쓰기 때문에, 한 번 터치하면 Hello 센서와 똑같이 잠금 화면이 풀리고, Hello 센서가 없는 데스크톱 PC나 외장 키보드에서도 됩니다. 게다가 Hello보다 더 나아갑니다. 같은 터치로 SSH와 Git 커밋에 서명하고, 1Password와 Bitwarden을 잠금 해제하고, TOTP 코드를 꺼낼 수 있으며, 같은 키를 macOS와 Linux에서도 쓸 수 있습니다."),
  ("패스키나 FIDO를 지원하나요",
   "아니요. immurok은 FIDO 기기가 아닙니다. 웹사이트에 패스키나 보안 키로 등록되지 않고, YubiKey를 대신하지도 않습니다. 한 층 아래, 바로 눈앞의 컴퓨터에서 일합니다. 화면 잠금 해제, sudo와 관리자 프롬프트 승인, SSH와 Git 서명, 비밀번호 관리자 잠금 해제, TOTP 코드. 웹사이트 로그인에는 패스키나 보안 키를 그대로 쓰세요. 나머지는 immurok이 맡고, 저희 중 많은 사람이 둘 다 씁니다."),
  ("ChromeOS를 지원하나요",
   "아니요. ChromeOS는 서드파티 소프트웨어가 화면 잠금 해제나 시스템 인증에 끼어들 방법을 열어 두지 않아서, immurok이 붙을 자리가 없습니다. macOS 13 이상, Windows 10과 11, 그리고 대부분의 Linux 배포판에서 동작합니다."),
  ("키 하나를 여러 컴퓨터에서 쓸 수 있나요",
   "네, 최대 두 대까지 되지만 연결은 한 번에 한 대입니다. 키는 각각 고유한 키를 가진 독립된 페어링 두 개를 갖고 있어서 두 컴퓨터 모두 묶인 상태로 남지만, 통신하는 상대는 언제나 한 대뿐입니다. 손가락 하나를 전환용 손가락으로 등록해 두고, 그 손가락을 대면 키가 한 컴퓨터에서 다른 컴퓨터로 넘어가며 대상 컴퓨터가 알아서 다시 연결합니다. 한 컴퓨터를 제거하면 그 페어링만 지워지고, 다른 컴퓨터와 등록된 지문은 그대로 남습니다."),
  ("1Password, Bitwarden, LastPass, Proton Pass를 잠금 해제할 수 있나요",
   "네, 네 가지 모두 macOS, Windows, Linux에서 지원합니다. 관리자 앱이 잠금 해제 창을 띄우면, 한 번 터치로 키에 저장된 전용 비밀번호를 입력하고 제출합니다. 이 비밀번호는 로그인 비밀번호와 따로 저장되고 따로 켜고 끕니다. 서명된 허용 목록에 있는 앱만 이 비밀번호를 받습니다."),
  ("USB로 연결할 수 있나요",
   "충전에만 씁니다. USB-C 포트는 배터리를 충전할 뿐 데이터는 오가지 않습니다. 페어링, 지문 결과, 그 밖의 모든 것은 Bluetooth LE로 오가므로 컴퓨터에 Bluetooth가 필요하고, 작업 중에 키가 포트를 차지하지 않습니다."),
  ("배터리를 교체할 수 있나요",
   "네. 키는 USB-C로 충전하는 110 mAh 충전식 리튬 셀로 동작하며, 정상 사용 기준 한 번 충전으로 한 달 이상 갑니다. 특주품이 아니라 시중에서 구할 수 있는 표준 규격이라 직접 바꿀 수 있습니다. 먼저 키의 페어링을 해제하거나 공장 초기화를 하세요. 페어링된 키의 케이스를 열면 탬퍼 스위치가 작동해 데이터가 지워집니다. 셀을 바꾸고 케이스를 닫은 뒤 다시 페어링하면 됩니다."),
  ("보안은 어떤가요? 지문은 어디에 저장되나요?",
   "기기 안에만 저장되고, 대조도 기기 안에서 이루어집니다. 컴퓨터의 디스크나 네트워크, 클라우드 서비스에는 전혀 전달되지 않습니다. 블루투스로 오가는 것은 HMAC로 서명된 일치 알림뿐이며 지문 자체는 나가지 않습니다. 페어링은 기기와 컴퓨터 사이의 직접 ECDH 교환입니다. 펌웨어 업데이트는 서명되어 있고 설치 전에 검증합니다. 계정도 서버도 텔레메트리도 없으므로 오프라인에서 완결되며, 저희가 사라져도 계속 동작합니다."),
  ("오픈소스인가요?",
   "모든 소스 코드가 GitHub에 공개되어 있고 라이선스는 두 가지입니다. macOS, Windows, Linux 앱은 PAM 모듈과 Windows Credential Provider를 포함해 Apache 2.0 오픈소스입니다. 펌웨어와 하드웨어는 BSL 1.1의 소스 공개 라이선스이며 2030년에 Apache 2.0으로 전환됩니다. 전부 읽고 수정하고 직접 빌드해 자기 기기에 써 넣을 수 있습니다. 전환 전까지 유보하는 권리는 경쟁 하드웨어를 판매하는 것뿐입니다."),
  ("펌웨어를 직접 빌드해서 올릴 수 있나요",
   "네. 펌웨어와 하드웨어 소스는 공개되어 있고, 기판에 프로그래밍 인터페이스가 있어서 펌웨어를 직접 빌드해 올릴 수 있습니다. 열기 전에 키를 초기화하세요. 페어링된 키를 열면 탬퍼 스위치가 작동합니다. 직접 빌드한 펌웨어를 올린 기기는 보증 대상에서 빠지고, 공식 펌웨어 업데이트도 더 이상 받지 못합니다."),
  ("YubiKey, 비밀번호 관리자, Touch ID와는 어떻게 다른가요?",
   "계층이 달라서 함께 쓸 수 있습니다. YubiKey와 패스키는 웹사이트에 대해 본인임을 증명합니다. immurok은 눈앞의 컴퓨터에서 비밀번호를 입력하는 번거로움을 없앱니다. 화면 잠금 해제, sudo, 관리자 승인, SSH와 Git 서명이 그렇습니다. 비밀번호 관리자는 비밀번호를 보관하지만, immurok은 macOS, Windows, Linux에서 1Password와 Bitwarden을 터치 한 번으로 잠금 해제하고 TOTP 시드를 기기 안에 보관해 2단계 인증 시드가 데스크톱 앱에 남지 않게 합니다. Touch ID는 Apple 자체 센서로 Secure Enclave와 결합되어 있어 서드파티가 쓸 수 없고, Mac mini나 외장 키보드에는 아예 없습니다. immurok은 독립된 기기이며, sudo와 관리자 승인은 PAM이라는 실제 시스템 메커니즘을 통하고 화면 잠금 해제는 별도로 문서화된 경로를 사용합니다."),
  ("Mac용 단독 Touch ID가 있나요?",
   "Apple에서는 나오지 않습니다. Touch ID는 MacBook에 내장된 것과 Touch ID 탑재 Magic Keyboard뿐이며, 이 키보드는 US$149에서 US$199이고 Apple Silicon Mac이 필요하며 센서가 키보드에 묶여 있습니다. 단독 Touch ID 센서는 존재하지 않고, Touch ID가 Secure Enclave와 결합되어 있어 서드파티가 만들 수도 없습니다. immurok이 그에 가장 가까운 제품입니다. 지금 쓰는 키보드 옆 책상 위에 두는 독립형 무선 지문 키로, Mac mini, Mac Studio, iMac, 덮어 둔 MacBook에서 화면 잠금 해제, sudo와 관리자 승인, 1Password와 Bitwarden 잠금 해제, SSH와 Git 커밋 서명을 처리합니다. Touch ID가 아니고 그런 척하지도 않습니다. 자체 센서와 자체 보안 모델을 가진 별도의 기기이며 Windows와 Linux에서도 씁니다."),
  ("구독이 필요한가요?",
   "필요 없습니다. 구독도, 계정도, 클라우드 서비스도 없습니다. 기기 값을 한 번만 내면 됩니다. macOS, Windows, Linux 앱과 펌웨어 업데이트 모두 무료입니다. 기기를 인터넷에 한 번도 연결하지 않아도 아무것도 멈추지 않습니다. 연결할 필요가 없기 때문입니다."),
  ("초기화는 어떻게 하나요? 분실하면 어떻게 되나요?",
   "버튼을 약 10초간 누르고 있으면 공장 초기화가 됩니다. 페어링 키, 등록된 모든 지문, 저장된 자격 증명이 모두 지워지고 다시 페어링할 수 있는 상태로 재시작합니다. 되돌릴 수 없습니다. 완전 초기화 없이 다른 컴퓨터로 옮기려면 앱에서 페어링 해제를 선택하세요. 분실하더라도 지문을 빼낼 수는 없습니다. 템플릿은 하드웨어를 벗어나지 않으며, 케이스를 강제로 열면 변조 감지 스위치가 작동해 모든 데이터를 지우고 표시등이 빨간색으로 고정됩니다. 모든 제품에 1년 보증이 포함됩니다. 지원 연락처는 사용 설명서와 앱에 안내되어 있습니다."),
 ]},

"ru": {
 "og": "ru_RU",
 "name": "Русский",
 "title": "immurok: цена, где купить и совместимость | Беспроводной ключ по отпечатку для Mac, Windows и Linux",
 "desc": "Цена immurok (US$69), где купить, в какие страны отправляем, поддерживаемые системы, безопасность, подписка и сброс.",
 "lead": "Вопросы, которые нам задают чаще всего, и ответы на них. То же содержание, что и на англоязычном сайте.",
 "cta": "Купить · US$69",
 "back": "Открыть полный сайт на английском",
 "qa": [
  ("С какими компьютерами и системами он работает?",
   "macOS 13.0 и новее, Windows 10 и 11, а также большинство дистрибутивов Linux. Приложение для Mac собрано единым универсальным бинарником для Apple Silicon и Intel. Для Windows есть нативные установщики x64 и Arm64, интеграция идёт через Credential Provider, поэтому работает и на экране блокировки. Для Linux это демон на Rust с интеграцией в PAM и polkit, проверенный на Ubuntu, Fedora, Arch и Debian и собирающийся на большинстве других дистрибутивов. Поскольку ключ является отдельным Bluetooth-устройством, а не встроенным в ноутбук датчиком, он одинаково работает с Mac mini, Mac Studio, iMac, закрытым MacBook, внешней клавиатурой и настольным ПК. Один ключ можно привязать сразу к двум компьютерам и переключаться между ними отдельным пальцем."),
  ("Работает ли он с Windows Hello?",
   "Это не устройство Windows Hello, и ему это не нужно. Windows Hello представляет собой систему Microsoft для датчиков, встроенных в ноутбук или в сертифицированную клавиатуру или веб-камеру. immurok выполняет вход другим путём: через Credential Provider, который работает внутри экрана входа Windows. Одно касание снимает блокировку экрана точно так же, как датчик Hello, на любом настольном ПК или внешней клавиатуре, где датчика Hello нет. И он идёт дальше Hello. Тем же касанием подписываются коммиты SSH и Git, разблокируются 1Password и Bitwarden, выдаются коды TOTP, а тот же ключ работает и на macOS, и на Linux."),
  ("Поддерживает ли он passkey или FIDO?",
   "Нет. immurok не является FIDO-устройством. Он не регистрируется на сайтах как passkey или ключ безопасности и не заменяет YubiKey. Он работает уровнем ниже, на компьютере перед вами: разблокировка экрана, запросы sudo и администратора, подписи SSH и Git, разблокировка менеджера паролей и коды TOTP. Оставьте passkey или ключ безопасности для входа на сайты; immurok берёт на себя остальное, и многие из нас пользуются и тем, и другим."),
  ("Поддерживается ли ChromeOS?",
   "Нет. ChromeOS не даёт стороннему ПО никакой возможности участвовать в разблокировке экрана или системной аутентификации, так что immurok там просто некуда встроиться. Он работает с macOS 13 и новее, Windows 10 и 11 и большинством дистрибутивов Linux."),
  ("Можно ли использовать один ключ с несколькими компьютерами?",
   "Да, максимум с двумя компьютерами, подключаясь к одному за раз. Ключ хранит два независимых сопряжения, каждое со своими ключами, так что обе машины остаются привязанными, но общается он в каждый момент только с одной. Один палец вы регистрируете как палец переключения. Касание им передаёт ключ от одного компьютера другому, и целевой компьютер переподключается сам. Удаление одного компьютера стирает только его сопряжение; второй компьютер и ваши отпечатки остаются нетронутыми."),
  ("Разблокирует ли он 1Password, Bitwarden, LastPass или Proton Pass?",
   "Да, все четыре поддерживаются на macOS, Windows и Linux. Когда менеджер показывает окно разблокировки, касание подставляет отдельный пароль, который хранится на ключе отдельно от пароля входа и включается отдельно, и отправляет его. Получить его могут только приложения из подписанного списка разрешённых."),
  ("Можно ли подключить его по USB?",
   "Только для зарядки. Порт USB-C заряжает аккумулятор и не передаёт данные. Сопряжение, результаты проверки отпечатка и всё остальное идут по Bluetooth LE, так что компьютеру нужен Bluetooth, а ключ во время работы не занимает ни одного порта."),
  ("Можно ли заменить аккумулятор?",
   "Да. Ключ работает от перезаряжаемого литиевого элемента на 110 мА·ч, заряжается по USB-C и при обычном использовании держит больше месяца на одном заряде. Это стандартный типоразмер, а не заказная деталь, и вы можете заменить его сами. Сначала отвяжите ключ или сбросьте его до заводских настроек: вскрытие корпуса сопряжённого ключа срабатывает датчик вскрытия и стирает его. Замените элемент, закройте корпус и выполните сопряжение заново."),
  ("Насколько это безопасно? Где хранятся отпечатки?",
   "На самом устройстве и больше нигде. Шаблоны отпечатков хранятся и сравниваются внутри ключа. Они не попадают ни на диск компьютера, ни в сеть, ни в облако. По Bluetooth передаётся только подписанное HMAC уведомление о совпадении, но не сам отпечаток. При сопряжении происходит прямой обмен ECDH между устройством и вашей машиной. Обновления прошивки подписаны и проверяются перед установкой. Нет аккаунта, нет сервера, нет телеметрии: всё работает офлайн и продолжит работать, даже если нас не станет."),
  ("Это открытый исходный код?",
   "Весь исходный код опубликован на GitHub под двумя разными лицензиями. Приложения для macOS, Windows и Linux, включая модули PAM и Credential Provider для Windows, открыты под Apache 2.0. Прошивка и аппаратная часть доступны по BSL 1.1 и перейдут на Apache 2.0 в 2030 году. Всё можно прочитать, изменить, собрать и прошить в собственное устройство. До перехода мы оставляем за собой единственное право: продавать конкурирующее оборудование."),
  ("Могу ли я собрать и прошить свою прошивку?",
   "Да. Исходники прошивки и железа открыты, а на плате есть интерфейс программирования, так что вы можете собрать свою прошивку и прошить её. Перед вскрытием сбросьте ключ, потому что вскрытие сопряжённого ключа срабатывает датчик вскрытия. Как только устройство работает на собранной вами прошивке, оно снимается с гарантии и больше не получает официальные обновления прошивки."),
  ("Чем это отличается от YubiKey, менеджера паролей или Touch ID?",
   "Это другой уровень, и они дополняют друг друга. YubiKey и passkeys доказывают сайту, кто вы. immurok убирает возню с паролем на той машине, что перед вами: разблокировка экрана, sudo, запросы администратора, подпись SSH и Git. Менеджер паролей хранит пароли; immurok разблокирует 1Password и Bitwarden одним касанием на macOS, Windows и Linux и держит секреты TOTP на самом устройстве, чтобы сиды двухфакторной аутентификации не лежали в настольном приложении. Touch ID является собственным датчиком Apple, сращённым с Secure Enclave, закрытым для сторонних разработчиков, и на Mac mini или внешней клавиатуре его просто нет. immurok представляет собой независимое устройство: sudo и запросы администратора идут через PAM, реальный системный механизм, а разблокировка экрана использует отдельно задокументированный путь."),
  ("Есть ли отдельный Touch ID для Mac?",
   "От Apple нет. Touch ID бывает только встроенным в MacBook и в Magic Keyboard с Touch ID, которая стоит от US$149 до US$199, требует Mac на Apple Silicon и привязывает датчик к клавиатуре, которая вам может быть не нужна. Отдельного датчика Touch ID не существует, а поскольку Touch ID сращён с Secure Enclave, сторонний производитель сделать его тоже не может. immurok ближе всего к этому: отдельный беспроводной ключ с датчиком отпечатка, который лежит на столе рядом с той клавиатурой, что у вас уже есть. На Mac mini, Mac Studio, iMac или закрытом MacBook он разблокирует экран, подтверждает sudo и запросы администратора, разблокирует 1Password и Bitwarden и подписывает коммиты SSH и Git. Это не Touch ID, и он не притворяется им: это отдельное устройство со своим датчиком и своей моделью безопасности, которое к тому же работает на Windows и Linux."),
  ("Нужна ли подписка?",
   "Нет. Ни подписки, ни аккаунта, ни облачного сервиса. Вы платите за устройство один раз. Приложения для macOS, Windows и Linux бесплатны, обновления прошивки тоже. Ничего не перестанет работать, даже если вы никогда не подключите устройство к интернету, потому что ему это не нужно."),
  ("Как сбросить и что делать при потере?",
   "Удерживайте кнопку около десяти секунд для сброса к заводским настройкам. Устройство стирает всё: ключи сопряжения, все записанные отпечатки и сохранённые учётные данные, и перезапускается готовым к новому сопряжению. Отменить это нельзя. Чтобы передать ключ на другой компьютер без полного сброса, выберите в приложении «Отвязать». Если ключ потерян, извлечь отпечатки из него невозможно: шаблоны не покидают железо, а вскрытие корпуса срабатывает как защита от вмешательства, стирает всё и оставляет индикатор гореть красным. На каждое устройство даётся год гарантии. Адрес поддержки указан в руководстве пользователя и в приложении."),
 ]},

"nl": {
 "og": "nl_NL",
 "name": "Nederlands",
 "title": "immurok: prijs, waar te koop en compatibiliteit | Draadloze vingerafdruksleutel voor Mac, Windows en Linux",
 "desc": "Prijs van immurok (US$69), waar te koop, verzendlanden, ondersteunde systemen, beveiliging, abonnement en resetten.",
 "lead": "De vragen die we het vaakst krijgen over immurok, beantwoord. Zelfde inhoud als de Engelse site.",
 "cta": "Nu kopen · US$69",
 "back": "Bekijk de volledige site in het Engels",
 "qa": [
  ("Met welke computers en besturingssystemen werkt hij?",
   "macOS 13.0 of nieuwer, Windows 10 en 11, en de meeste Linux-distributies. De Mac-app is één universele build voor Apple Silicon en Intel. Windows heeft native x64- en Arm64-installers en integreert via een Credential Provider, dus hij werkt op het vergrendelscherm. Linux is een daemon in Rust met PAM- en polkit-integratie, getest op Ubuntu, Fedora, Arch en Debian, en hij bouwt op de meeste andere distributies. Omdat de sleutel een los Bluetooth-apparaat is en geen sensor in een laptop, werkt hij hetzelfde op een Mac mini, een Mac Studio, een iMac, een dichtgeklapte MacBook, een extern toetsenbord of een desktop-pc. Eén sleutel kan aan twee computers tegelijk gekoppeld zijn en met een aparte vinger schakel je ertussen."),
  ("Werkt het met Windows Hello?",
   "Het is geen Windows Hello-apparaat, en dat hoeft ook niet. Windows Hello is het raamwerk van Microsoft voor sensoren die in een laptop of in een gecertificeerd toetsenbord of webcam zijn ingebouwd. immurok meldt je op een andere manier aan: via een Credential Provider die in het aanmeldscherm van Windows draait. Eén aanraking ontgrendelt het vergrendelscherm dus precies zoals een Hello-sensor, op elke desktop-pc of elk extern toetsenbord waar geen Hello-sensor zit. En het gaat verder dan Hello. Dezelfde aanraking ondertekent SSH- en Git-commits, ontgrendelt 1Password en Bitwarden en geeft TOTP-codes vrij, en dezelfde sleutel werkt ook op macOS en Linux."),
  ("Ondersteunt het passkeys of FIDO?",
   "Nee. immurok is geen FIDO-apparaat. Het registreert zich bij websites niet als passkey of beveiligingssleutel, en het vervangt geen YubiKey. Het werkt een laag lager, op de machine voor je neus: schermontgrendeling, sudo- en beheerdersprompts, SSH- en Git-ondertekening, ontgrendelen van je wachtwoordmanager en TOTP-codes. Houd je passkeys of beveiligingssleutel voor het inloggen op websites; immurok doet de rest, en velen van ons gebruiken beide."),
  ("Ondersteunt het ChromeOS?",
   "Nee. ChromeOS geeft software van derden geen enkele manier om mee te doen aan schermontgrendeling of systeemauthenticatie, dus er is niets waar immurok op kan aanhaken. Het werkt met macOS 13 of nieuwer, Windows 10 en 11 en de meeste Linux-distributies."),
  ("Kan ik één sleutel met meer dan één computer gebruiken?",
   "Ja, met maximaal twee computers, verbonden met één tegelijk. De sleutel bewaart twee onafhankelijke koppelingen, elk met eigen sleutels, zodat beide machines gebonden blijven, maar hij praat altijd met maar één van de twee. Je registreert één vinger als wisselvinger. Raak je die aan, dan gaat de sleutel van de ene computer naar de andere, en de doelcomputer maakt vanzelf opnieuw verbinding. Een computer verwijderen wist alleen die koppeling; de andere computer en je geregistreerde vingerafdrukken blijven onaangeroerd."),
  ("Ontgrendelt het 1Password, Bitwarden, LastPass of Proton Pass?",
   "Ja, alle vier, op macOS, Windows en Linux. Als de manager zijn ontgrendelscherm toont, vult één aanraking een apart wachtwoord in dat op de sleutel staat, los van je aanmeldwachtwoord opgeslagen en apart in te schakelen, en verstuurt het. Alleen apps op een ondertekende toegestane lijst krijgen het ooit te zien."),
  ("Kan ik hem via USB aansluiten?",
   "Alleen om op te laden. De USB-C-poort laadt de accu en draagt geen data over. Koppelen, vingerafdrukresultaten en al het andere gaan via Bluetooth LE, dus je computer heeft Bluetooth nodig en de sleutel neemt tijdens het werken geen poort in."),
  ("Is de accu vervangbaar?",
   "Ja. De sleutel werkt op een oplaadbare lithiumcel van 110 mAh die via USB-C laadt en bij normaal gebruik meer dan een maand per lading meegaat. Het is een standaardmaat uit de winkel, geen maatwerkonderdeel, en je kunt hem zelf vervangen. Ontkoppel de sleutel eerst of zet hem terug naar fabrieksinstellingen: de behuizing van een gekoppelde sleutel openen activeert de sabotageschakelaar en wist hem. Vervang de cel, sluit de behuizing en koppel opnieuw."),
  ("Hoe veilig is het? Waar staan mijn vingerafdrukken?",
   "Op het apparaat, en nergens anders. De vingerafdruksjablonen worden op de sleutel zelf opgeslagen en daar vergeleken. Ze bereiken nooit de schijf van je computer, het netwerk of een clouddienst. Over Bluetooth gaat alleen een met HMAC ondertekende melding dat de afdruk klopte, nooit de afdruk zelf. Koppelen is een directe ECDH-uitwisseling tussen apparaat en computer. Firmware-updates zijn ondertekend en worden voor installatie geverifieerd. Er is geen account, geen server en geen telemetrie: alles werkt offline en zou blijven werken als wij verdwijnen."),
  ("Is het open source?",
   "Alle broncode staat publiek op GitHub, onder twee verschillende licenties. De apps voor macOS, Windows en Linux, inclusief de PAM-modules en de Windows Credential Provider, zijn open source onder Apache 2.0. Firmware en hardware zijn source-available onder BSL 1.1 en gaan in 2030 over naar Apache 2.0. Je kunt alles lezen, aanpassen, zelf bouwen en op je eigen apparaat flashen. Het enige recht dat we tot die overgang voorbehouden is het verkopen van concurrerende hardware."),
  ("Kan ik mijn eigen firmware bouwen en flashen?",
   "Ja. De broncode van firmware en hardware is openbaar, en de printplaat heeft een programmeerinterface zodat je je eigen firmware kunt bouwen en flashen. Reset de sleutel voordat je hem opent, want een gekoppelde sleutel openen activeert de sabotageschakelaar. Zodra een exemplaar op zelfgebouwde firmware draait, vervalt de garantie en ontvangt het geen officiële firmware-updates meer."),
  ("Wat is het verschil met een YubiKey, een wachtwoordmanager of Touch ID?",
   "Andere laag, en ze vullen elkaar aan. Een YubiKey en passkeys bewijzen aan een website wie je bent. immurok haalt de wachtwoordwrijving weg op de machine die voor je staat: scherm ontgrendelen, sudo, beheerdersvragen, SSH- en Git-ondertekening. Een wachtwoordmanager bewaart je wachtwoorden; immurok ontgrendelt 1Password en Bitwarden met een aanraking op macOS, Windows en Linux en houdt TOTP-seeds op het apparaat, zodat je tweefactorgeheimen niet in een desktop-app staan. Touch ID is Apple's eigen sensor, vastgeklonken aan de Secure Enclave, gesloten voor derden, en bestaat gewoonweg niet op een Mac mini of een extern toetsenbord. immurok is een zelfstandig apparaat: sudo en beheerdersvragen lopen via PAM, een echt systeemmechanisme, en schermontgrendeling gebruikt een apart gedocumenteerde route."),
  ("Bestaat er een losse Touch ID voor de Mac?",
   "Van Apple niet. Touch ID zit alleen ingebouwd in MacBooks en in het Magic Keyboard met Touch ID, dat US$149 tot US$199 kost, een Mac met Apple Silicon vereist en de sensor vastmaakt aan een toetsenbord dat je misschien niet wilt. Een losse Touch ID-sensor bestaat niet, en omdat Touch ID vastzit aan de Secure Enclave kan een derde partij er ook geen maken. immurok komt het dichtst in de buurt: een zelfstandige draadloze vingerafdruksleutel die op je bureau ligt naast het toetsenbord dat je al gebruikt. Op een Mac mini, Mac Studio, iMac of dichtgeklapte MacBook ontgrendelt hij het scherm, keurt hij sudo en beheerdersvragen goed, ontgrendelt hij 1Password en Bitwarden en ondertekent hij SSH- en Git-commits. Het is geen Touch ID en doet zich niet zo voor: het is een apart apparaat met een eigen sensor en een eigen beveiligingsmodel, en het werkt ook op Windows en Linux."),
  ("Heb ik een abonnement nodig?",
   "Nee. Geen abonnement, geen account, geen clouddienst. Je betaalt één keer voor het apparaat. De apps voor macOS, Windows en Linux zijn gratis, en firmware-updates ook. Er stopt niets met werken als je het apparaat nooit met internet verbindt, want dat hoeft niet."),
  ("Hoe reset ik hem, en wat als ik hem kwijtraak?",
   "Houd de knop ongeveer tien seconden ingedrukt voor een fabrieksreset. Het apparaat wist alles: koppelsleutels, elke opgeslagen vingerafdruk en bewaarde inloggegevens, en start opnieuw op, klaar om te koppelen. Dit kun je niet ongedaan maken. Wil je de sleutel naar een andere computer verhuizen zonder alles te wissen, kies dan Ontkoppelen in de app. Raak je hem kwijt, dan kan niemand je vingerafdrukken eruit halen: de sjablonen verlaten de hardware nooit, en de behuizing openbreken activeert een sabotageschakelaar die alles wist en het lampje continu rood laat branden. Elk apparaat heeft een jaar garantie. Het supportadres staat in de handleiding en in de app."),
 ]},

"pl": {
 "og": "pl_PL",
 "name": "Polski",
 "title": "immurok: cena, gdzie kupić i zgodność | Bezprzewodowy klucz z czytnikiem linii papilarnych do Mac, Windows i Linux",
 "desc": "Cena immurok (US$69), gdzie kupić, kraje wysyłki, obsługiwane systemy, bezpieczeństwo, abonament i reset.",
 "lead": "Najczęstsze pytania o immurok wraz z odpowiedziami. Ta sama treść co na stronie angielskiej.",
 "cta": "Kup teraz · US$69",
 "back": "Zobacz pełną stronę po angielsku",
 "qa": [
  ("Z jakimi komputerami i systemami działa?",
   "macOS 13.0 lub nowszy, Windows 10 i 11 oraz większość dystrybucji Linuksa. Aplikacja na Maca to jedna uniwersalna kompilacja dla Apple Silicon i Intela. Windows ma natywne instalatory x64 i Arm64 oraz integrację przez Credential Provider, więc działa na ekranie blokady. Linux to demon w Rust z integracją PAM i polkit, przetestowany na Ubuntu, Fedorze, Archu i Debianie, kompilujący się na większości innych dystrybucji. Ponieważ klucz jest osobnym urządzeniem Bluetooth, a nie czytnikiem wbudowanym w laptopa, działa tak samo z Mac mini, Mac Studio, iMakiem, zamkniętym MacBookiem, klawiaturą zewnętrzną i pecetem. Jeden klucz można powiązać z dwoma komputerami naraz i przełączać się między nimi osobnym palcem."),
  ("Czy działa z Windows Hello?",
   "To nie jest urządzenie Windows Hello i nie musi nim być. Windows Hello to mechanizm Microsoftu dla czujników wbudowanych w laptopa albo w certyfikowaną klawiaturę lub kamerę. immurok loguje cię inną drogą: przez Credential Provider działający wewnątrz ekranu logowania Windows. Jedno dotknięcie odblokowuje więc ekran blokady dokładnie tak, jak zrobiłby to czujnik Hello, na każdym komputerze stacjonarnym i każdej zewnętrznej klawiaturze, gdzie czujnika Hello nie ma. I idzie dalej niż Hello. To samo dotknięcie podpisuje commity SSH i Git, odblokowuje 1Password i Bitwarden i wydaje kody TOTP, a ten sam klucz działa też na macOS i Linuksie."),
  ("Czy obsługuje passkeys lub FIDO?",
   "Nie. immurok nie jest urządzeniem FIDO. Nie rejestruje się w serwisach jako passkey ani klucz bezpieczeństwa i nie zastępuje YubiKeya. Działa warstwę niżej, na komputerze przed tobą: odblokowanie ekranu, monity sudo i administratora, podpisywanie SSH i Git, odblokowanie menedżera haseł i kody TOTP. Passkeys lub klucz bezpieczeństwa zostaw do logowania w serwisach; immurok zajmuje się resztą, a wielu z nas używa obu."),
  ("Czy obsługuje ChromeOS?",
   "Nie. ChromeOS nie daje oprogramowaniu firm trzecich żadnej możliwości udziału w odblokowywaniu ekranu ani uwierzytelnianiu systemowym, więc immurok nie ma się do czego podpiąć. Działa z macOS 13 lub nowszym, Windows 10 i 11 oraz większością dystrybucji Linuksa."),
  ("Czy mogę używać jednego klucza z więcej niż jednym komputerem?",
   "Tak, maksymalnie z dwoma komputerami, połączony z jednym naraz. Klucz przechowuje dwa niezależne parowania, każde z własnymi kluczami, więc obie maszyny pozostają powiązane, ale w danej chwili rozmawia tylko z jedną. Jeden palec rejestrujesz jako palec przełączający. Jego dotknięcie przekazuje klucz z jednego komputera na drugi, a komputer docelowy sam się ponownie łączy. Usunięcie jednego komputera kasuje tylko to parowanie; drugi komputer i zarejestrowane odciski zostają nietknięte."),
  ("Czy odblokowuje 1Password, Bitwarden, LastPass lub Proton Pass?",
   "Tak, wszystkie cztery, na macOS, Windows i Linux. Gdy menedżer pokaże okno odblokowania, dotknięcie wpisuje osobne hasło przechowywane na kluczu, zapisane oddzielnie od hasła logowania i włączane oddzielnie, i je zatwierdza. Dostają je wyłącznie aplikacje z podpisanej listy dozwolonych."),
  ("Czy mogę podłączyć go przez USB?",
   "Tylko do ładowania. Port USB-C ładuje akumulator i nie przesyła danych. Parowanie, wyniki odczytu odcisku i wszystko inne idzie przez Bluetooth LE, więc komputer potrzebuje Bluetootha, a klucz w trakcie pracy nie zajmuje żadnego portu."),
  ("Czy akumulator da się wymienić?",
   "Tak. Klucz pracuje na ładowalnym ogniwie litowym 110 mAh, ładowanym przez USB-C, które przy normalnym użyciu wytrzymuje ponad miesiąc na jednym ładowaniu. To standardowy, dostępny w sklepach rozmiar, a nie część na zamówienie, i możesz wymienić je samodzielnie. Najpierw rozparuj klucz albo przywróć ustawienia fabryczne: otwarcie obudowy sparowanego klucza uruchamia wyłącznik antysabotażowy i kasuje go. Wymień ogniwo, zamknij obudowę i sparuj ponownie."),
  ("Jak to jest zabezpieczone? Gdzie są moje odciski?",
   "W urządzeniu i nigdzie indziej. Wzorce odcisków są przechowywane i porównywane wewnątrz klucza. Nigdy nie trafiają na dysk komputera, do sieci ani do chmury. Przez Bluetooth idzie tylko podpisane HMAC powiadomienie o dopasowaniu, nigdy sam odcisk. Parowanie to bezpośrednia wymiana ECDH między urządzeniem a komputerem. Aktualizacje firmware są podpisane i weryfikowane przed instalacją. Nie ma konta, serwera ani telemetrii: wszystko działa offline i będzie działać, nawet gdyby nas zabrakło."),
  ("Czy to open source?",
   "Cały kod źródłowy jest publiczny na GitHubie, na dwóch różnych licencjach. Aplikacje na macOS, Windows i Linux, wraz z modułami PAM i Credential Providerem dla Windows, są otwarte na licencji Apache 2.0. Firmware i sprzęt są source-available na BSL 1.1 i przechodzą na Apache 2.0 w 2030 roku. Możesz wszystko przeczytać, zmienić, skompilować i wgrać na własne urządzenie. Do czasu konwersji zastrzegamy sobie tylko jedno prawo: sprzedaż konkurencyjnego sprzętu."),
  ("Czy mogę zbudować i wgrać własny firmware?",
   "Tak. Źródła firmware'u i sprzętu są publiczne, a płytka ma interfejs programowania, więc możesz zbudować własny firmware i go wgrać. Zresetuj klucz przed otwarciem, bo otwarcie sparowanego klucza uruchamia wyłącznik antysabotażowy. Gdy egzemplarz działa na firmware zbudowanym przez ciebie, traci gwarancję i nie otrzymuje już oficjalnych aktualizacji firmware'u."),
  ("Czym różni się od YubiKey, menedżera haseł albo Touch ID?",
   "To inna warstwa i dobrze się uzupełniają. YubiKey i passkeys dowodzą stronie internetowej, kim jesteś. immurok usuwa mordęgę z hasłem na komputerze, który masz przed sobą: odblokowanie ekranu, sudo, pytania administratora, podpisywanie SSH i Git. Menedżer haseł przechowuje hasła; immurok odblokowuje 1Password i Bitwarden dotknięciem na macOS, Windows i Linux i trzyma nasiona TOTP w samym urządzeniu, żeby sekrety dwuskładnikowe nie leżały w aplikacji na pulpicie. Touch ID to własny czytnik Apple, zespolony z Secure Enclave, zamknięty dla firm trzecich, a w Mac mini czy klawiaturze zewnętrznej po prostu go nie ma. immurok jest urządzeniem niezależnym: sudo i pytania administratora idą przez PAM, czyli prawdziwy mechanizm systemowy, a odblokowanie ekranu korzysta z osobno udokumentowanej ścieżki."),
  ("Czy istnieje samodzielny Touch ID do Maca?",
   "Od Apple nie. Touch ID jest tylko wbudowany w MacBooki i w Magic Keyboard z Touch ID, która kosztuje od US$149 do US$199, wymaga Maca z Apple Silicon i wiąże czytnik z klawiaturą, której możesz wcale nie chcieć. Samodzielny czytnik Touch ID nie istnieje, a ponieważ Touch ID jest zespolony z Secure Enclave, firma trzecia też go nie zrobi. immurok jest najbliżej tego: samodzielny bezprzewodowy klucz z czytnikiem linii papilarnych, który leży na biurku obok klawiatury, której już używasz. Na Mac mini, Mac Studio, iMacu albo zamkniętym MacBooku odblokowuje ekran, zatwierdza sudo i pytania administratora, odblokowuje 1Password i Bitwarden oraz podpisuje commity SSH i Git. To nie jest Touch ID i nie udaje go: to osobne urządzenie z własnym czytnikiem i własnym modelem bezpieczeństwa, które działa też na Windows i Linuksie."),
  ("Czy potrzebny jest abonament?",
   "Nie. Bez abonamentu, bez konta, bez usługi chmurowej. Płacisz raz za urządzenie. Aplikacje na macOS, Windows i Linux są darmowe, aktualizacje firmware też. Nic nie przestanie działać, jeśli nigdy nie podłączysz urządzenia do internetu, bo nie musi być podłączone."),
  ("Jak go zresetować i co, jeśli go zgubię?",
   "Przytrzymaj przycisk przez około dziesięć sekund, żeby przywrócić ustawienia fabryczne. Urządzenie kasuje wszystko: klucze parowania, wszystkie zapisane odciski i przechowywane poświadczenia, po czym uruchamia się gotowe do ponownego sparowania. Tego nie da się cofnąć. Aby przenieść klucz na inny komputer bez pełnego resetu, wybierz w aplikacji Rozparuj. Jeśli go zgubisz, nikt nie wydobędzie z niego twoich odcisków: wzorce nigdy nie opuszczają sprzętu, a otwarcie obudowy na siłę uruchamia zabezpieczenie, które kasuje wszystko i zostawia diodę świecącą na czerwono. Każde urządzenie ma rok gwarancji. Adres wsparcia znajdziesz w instrukcji i w aplikacji."),
 ]},

"id": {
 "og": "id_ID",
 "name": "Bahasa Indonesia",
 "title": "immurok: harga, cara beli, dan kompatibilitas | Kunci sidik jari nirkabel untuk Mac, Windows, dan Linux",
 "desc": "Harga immurok (US$69), cara membeli, negara pengiriman, sistem yang didukung, keamanan, langganan, dan cara reset.",
 "lead": "Pertanyaan yang paling sering kami terima tentang immurok, beserta jawabannya. Isinya sama dengan situs bahasa Inggris.",
 "cta": "Beli sekarang · US$69",
 "back": "Lihat situs lengkap dalam bahasa Inggris",
 "qa": [
  ("Kompatibel dengan komputer dan sistem operasi apa saja?",
   "macOS 13.0 atau lebih baru, Windows 10 dan 11, serta sebagian besar distribusi Linux. Aplikasi Mac berupa satu build universal untuk Apple Silicon dan Intel. Windows punya installer native x64 dan Arm64 dan terintegrasi sebagai Credential Provider, jadi bisa dipakai di layar kunci. Linux berupa daemon Rust dengan integrasi PAM dan polkit, sudah diuji di Ubuntu, Fedora, Arch, dan Debian, dan bisa dikompilasi di kebanyakan distribusi lain. Karena kuncinya adalah perangkat Bluetooth terpisah, bukan sensor yang tertanam di laptop, cara kerjanya sama pada Mac mini, Mac Studio, iMac, MacBook tertutup, keyboard eksternal, maupun PC desktop. Satu kunci bisa terhubung ke dua komputer sekaligus dan berpindah di antaranya lewat sidik jari khusus."),
  ("Apakah bisa dipakai dengan Windows Hello?",
   "Ini bukan perangkat Windows Hello, dan memang tidak perlu. Windows Hello adalah kerangka Microsoft untuk sensor yang tertanam di laptop atau di keyboard atau webcam bersertifikat. immurok memasukkan Anda lewat jalur lain: Credential Provider yang berjalan di dalam layar masuk Windows, jadi satu sentuhan membuka layar kunci persis seperti sensor Hello, di PC desktop atau keyboard eksternal mana pun yang tidak punya sensor Hello. Lalu ia melangkah lebih jauh dari Hello. Sentuhan yang sama menandatangani commit SSH dan Git, membuka 1Password dan Bitwarden, mengeluarkan kode TOTP, dan kunci yang sama juga bekerja di macOS dan Linux."),
  ("Apakah mendukung passkey atau FIDO?",
   "Tidak. immurok bukan perangkat FIDO. Ia tidak mendaftar ke situs web sebagai passkey atau kunci keamanan, dan tidak menggantikan YubiKey. Ia bekerja satu lapis di bawahnya, di komputer yang ada di depan Anda: membuka layar kunci, menyetujui prompt sudo dan admin, menandatangani SSH dan Git, membuka pengelola kata sandi, dan kode TOTP. Tetap pakai passkey atau kunci keamanan Anda untuk masuk ke situs web; immurok mengurus sisanya, dan banyak dari kami memakai keduanya."),
  ("Apakah mendukung ChromeOS?",
   "Tidak. ChromeOS tidak memberi perangkat lunak pihak ketiga jalan untuk ikut dalam pembukaan layar kunci atau autentikasi sistem, jadi tidak ada tempat bagi immurok untuk masuk. Ia bekerja dengan macOS 13 atau lebih baru, Windows 10 dan 11, dan sebagian besar distribusi Linux."),
  ("Bisakah satu kunci dipakai di lebih dari satu komputer?",
   "Bisa, dengan maksimal dua komputer, tersambung ke satu pada satu waktu. Kunci menyimpan dua pemasangan independen, masing-masing dengan kuncinya sendiri, jadi kedua mesin tetap terikat, tetapi ia hanya berbicara dengan satu di antaranya pada satu waktu. Anda mendaftarkan satu jari sebagai jari pengalih. Menyentuhnya memindahkan kunci dari satu komputer ke komputer lain, dan komputer tujuan menyambung kembali sendiri. Menghapus satu komputer hanya menghapus pemasangan itu; komputer satunya dan sidik jari yang terdaftar tidak tersentuh."),
  ("Apakah bisa membuka 1Password, Bitwarden, LastPass, atau Proton Pass?",
   "Ya, keempatnya, di macOS, Windows, dan Linux. Saat pengelola menampilkan layar bukanya, satu sentuhan mengisi kata sandi khusus yang tersimpan di kunci, disimpan terpisah dari kata sandi login dan diaktifkan terpisah, lalu mengirimkannya. Hanya aplikasi dalam daftar izin bertanda tangan yang pernah menerimanya."),
  ("Bisakah disambungkan lewat USB?",
   "Hanya untuk mengisi daya. Port USB-C mengisi baterai dan tidak membawa data. Pemasangan, hasil sidik jari, dan semua yang lain lewat Bluetooth LE, jadi komputer Anda butuh Bluetooth dan kunci tidak memakai port apa pun saat Anda bekerja."),
  ("Apakah baterainya bisa diganti?",
   "Bisa. Kunci ini memakai sel litium isi ulang 110 mAh yang diisi lewat USB-C dan tahan lebih dari sebulan pemakaian normal per pengisian. Ukurannya standar pasaran, bukan komponen khusus, dan Anda bisa menggantinya sendiri. Lepaskan pemasangan atau reset pabrik dulu: membuka casing kunci yang masih terpasang memicu sakelar anti-bongkar dan menghapusnya. Ganti sel, tutup casing, lalu pasangkan lagi."),
  ("Seberapa aman? Di mana sidik jari saya disimpan?",
   "Di dalam perangkat, dan tidak di tempat lain. Template sidik jari disimpan dan dicocokkan di dalam kunci itu sendiri. Data itu tidak pernah sampai ke disk komputer, jaringan, atau layanan cloud mana pun. Yang lewat Bluetooth hanya notifikasi bertanda tangan HMAC bahwa sidik jari cocok, bukan sidik jarinya. Pemasangan memakai pertukaran ECDH langsung antara perangkat dan komputer Anda. Pembaruan firmware ditandatangani dan diverifikasi sebelum dipasang. Tidak ada akun, server, maupun telemetri, jadi semuanya berjalan offline dan tetap berjalan meski kami menghilang."),
  ("Apakah open source?",
   "Seluruh kode sumber terbuka di GitHub, dengan dua lisensi berbeda. Aplikasi macOS, Windows, dan Linux, termasuk modul PAM dan Credential Provider untuk Windows, bersifat open source dengan lisensi Apache 2.0. Firmware dan perangkat kerasnya source-available dengan BSL 1.1 dan beralih ke Apache 2.0 pada 2030. Anda bisa membaca semuanya, memodifikasi, membangun sendiri, dan mem-flash ke unit Anda. Satu-satunya hak yang kami tahan sampai peralihan itu adalah menjual perangkat keras pesaing."),
  ("Bisakah saya membangun dan mem-flash firmware sendiri?",
   "Bisa. Sumber firmware dan perangkat kerasnya terbuka, dan PCB menyediakan antarmuka pemrograman sehingga Anda bisa membangun firmware sendiri dan mem-flash-nya. Reset kunci sebelum membukanya, karena membuka kunci yang masih terpasang memicu sakelar anti-bongkar. Begitu sebuah unit menjalankan firmware buatan Anda, garansinya gugur dan tidak lagi menerima pembaruan firmware resmi."),
  ("Apa bedanya dengan YubiKey, pengelola kata sandi, atau Touch ID?",
   "Lapisannya berbeda dan justru saling melengkapi. YubiKey dan passkey membuktikan identitas Anda kepada sebuah situs web. immurok menghilangkan repotnya mengetik kata sandi di komputer yang ada di depan Anda: membuka kunci layar, sudo, permintaan administrator, penandatanganan SSH dan Git. Pengelola kata sandi menyimpan kata sandi Anda; immurok membuka kunci 1Password dan Bitwarden dengan satu sentuhan di macOS, Windows, dan Linux, dan menyimpan seed TOTP di dalam perangkat, sehingga kunci dua faktor Anda tidak menumpuk di aplikasi desktop. Touch ID adalah sensor milik Apple sendiri, menyatu dengan Secure Enclave, tertutup bagi pihak ketiga, dan memang tidak ada di Mac mini atau keyboard eksternal. immurok adalah perangkat mandiri: sudo dan permintaan administrator lewat PAM, mekanisme sistem yang sebenarnya, sedangkan membuka kunci layar memakai jalur bantu yang didokumentasikan terpisah."),
  ("Apakah ada Touch ID mandiri untuk Mac?",
   "Dari Apple tidak ada. Touch ID hanya tersedia tertanam di MacBook dan di Magic Keyboard dengan Touch ID, yang harganya US$149 sampai US$199, butuh Mac dengan Apple Silicon, dan mengikat sensornya ke keyboard yang mungkin tidak Anda inginkan. Sensor Touch ID lepas tidak ada, dan karena Touch ID menyatu dengan Secure Enclave, pihak ketiga juga tidak bisa membuatnya. immurok adalah yang paling mendekati: kunci sidik jari nirkabel mandiri yang diletakkan di meja di samping keyboard yang sudah Anda pakai. Di Mac mini, Mac Studio, iMac, atau MacBook yang tertutup, ia membuka kunci layar, menyetujui sudo dan permintaan administrator, membuka kunci 1Password dan Bitwarden, serta menandatangani commit SSH dan Git. Ini bukan Touch ID dan tidak berpura-pura menjadi Touch ID: ini perangkat terpisah dengan sensor sendiri dan model keamanan sendiri, dan juga berjalan di Windows dan Linux."),
  ("Apakah perlu langganan?",
   "Tidak. Tanpa langganan, tanpa akun, tanpa layanan cloud. Anda membayar sekali untuk perangkatnya. Aplikasi macOS, Windows, dan Linux gratis, begitu juga pembaruan firmware. Tidak ada yang berhenti bekerja meski perangkat tidak pernah Anda sambungkan ke internet, karena memang tidak perlu."),
  ("Bagaimana cara reset, dan bagaimana kalau hilang?",
   "Tekan dan tahan tombolnya sekitar sepuluh detik untuk reset pabrik. Perangkat menghapus semuanya: kunci pemasangan, semua sidik jari yang terdaftar, dan kredensial yang tersimpan, lalu menyala ulang dalam keadaan siap dipasangkan lagi. Ini tidak bisa dibatalkan. Untuk memindahkan kunci ke komputer lain tanpa reset penuh, pilih Unpair di aplikasi. Kalau perangkatnya hilang, sidik jari Anda tidak bisa diambil: template tidak pernah keluar dari perangkat kerasnya, dan membuka paksa casing akan memicu sakelar anti-bongkar yang menghapus semuanya dan membuat lampunya menyala merah terus. Setiap unit disertai garansi satu tahun. Alamat dukungan tercantum di buku panduan dan tampil di aplikasi."),
 ]},

"zh-hans": {
 "code": "zh-Hans",
 "og": "zh_CN",
 "name": "简体中文",
 "title": "immurok 价格、购买方式与兼容性 | 适用于 Mac、Windows、Linux 的无线指纹钥匙",
 "desc": "immurok 的价格（US$69）、在哪购买、发货国家、支持的系统、安全性、是否需要订阅以及重置方法。",
 "lead": "关于 immurok 最常被问到的问题和答案。内容与英文站一致。",
 "cta": "立即购买 · US$69",
 "back": "查看完整英文站点",
 "qa": [
  ("支持哪些电脑和操作系统",
   "macOS 13.0 及以上、Windows 10 和 11，以及大多数 Linux 发行版。Mac 版是同时支持 Apple Silicon 和 Intel 的通用版本。Windows 版提供 x64 和 Arm64 原生安装包，通过 Credential Provider 集成，所以在锁屏界面上也能用。Linux 版是 Rust 写的守护进程，集成 PAM 和 polkit，在 Ubuntu、Fedora、Arch、Debian 上测试过，多数其他发行版也能编译。因为这把钥匙是独立的蓝牙设备，不是嵌在笔记本里的传感器，所以在 Mac mini、Mac Studio、iMac、合盖的 MacBook、外接键盘和台式 PC 上用法完全一样。一把设备可以同时绑定两台电脑，用一根专门的手指在两者之间切换。"),
  ("支持 Windows Hello 吗",
   "它不是 Windows Hello 设备，也不需要是。Windows Hello 是微软给笔记本内置传感器、认证键盘和摄像头准备的框架。immurok 走的是另一条路：一个跑在 Windows 登录界面里的 Credential Provider，所以触摸一下就能像 Hello 传感器一样解开锁屏，而且在没有 Hello 传感器的台式机和外接键盘上也一样能用。然后它比 Hello 走得更远。同一次触摸还能给 SSH 和 Git 提交签名、解锁 1Password 和 Bitwarden、放出 TOTP 验证码，同一把钥匙在 macOS 和 Linux 上也能用。"),
  ("支持 passkey 或 FIDO 吗",
   "不支持。immurok 不是 FIDO 设备。它不会作为 passkey 或安全密钥注册到网站上，也不能替代 YubiKey。它干的是低一层的活，在你面前这台电脑上：解锁屏幕、批准 sudo 和管理员提示、给 SSH 和 Git 签名、解锁密码管理器、放出 TOTP 验证码。登录网站继续用你的 passkey 或安全密钥，其余的交给 immurok，我们很多人两样都用。"),
  ("支持 ChromeOS 吗",
   "不支持。ChromeOS 不给第三方软件任何参与锁屏解锁或系统认证的入口，immurok 没有地方可以接进去。它支持 macOS 13 及以上、Windows 10 和 11，以及大多数 Linux 发行版。"),
  ("一把钥匙能在多台电脑上用吗",
   "能，最多两台，但同一时间只连接其中一台。钥匙内部保存两份独立的配对，各有各的密钥，两台电脑都一直绑着，但任一时刻只和其中一台通信。你把一根手指录成「切换指纹」，触摸它钥匙就从一台电脑切到另一台，目标电脑自动重连。移除其中一台只清掉那一份配对，另一台电脑和已录入的指纹不受影响。"),
  ("能解锁 1Password、Bitwarden、LastPass 或 Proton Pass 吗",
   "四个都可以，在 macOS、Windows 和 Linux 上都支持。密码管理器弹出解锁框时，触摸一下就会填入一段存在钥匙上的专用密码并提交，这段密码与登录密码分开保存、分开开关。只有在签名白名单里的应用才能拿到它。"),
  ("能用 USB 连接吗",
   "只能用来充电。USB-C 口只给电池充电，不走数据。配对、指纹结果和其他一切都走蓝牙 LE，所以电脑需要有蓝牙，而工作时钥匙不占任何接口。"),
  ("电池可以更换吗",
   "可以。钥匙用一块 110 mAh 的可充电锂电池，通过 USB-C 充电，正常使用一次充电能用一个多月。它是市面上的标准规格，不是定制件，你可以自己换。换之前先取消配对或恢复出厂设置：已配对的钥匙一开盖就会触发防拆开关，把数据全部擦掉。换好电池、合上外壳，再重新配对。"),
  ("安全性如何，指纹存在哪里",
   "存在设备里，别处没有。指纹模板保存在钥匙内部，比对也在钥匙内部完成，不会到你电脑的硬盘、网络或任何云服务上。蓝牙上传输的只是一条用 HMAC 签名的「匹配成功」通知，指纹本身不会出去。配对是设备和电脑之间直接做 ECDH 密钥交换。固件更新经过签名，安装前会验签。没有账号、没有服务器、没有遥测，所以全程离线可用，就算我们哪天不在了它也照样能用。"),
  ("是开源的吗",
   "全部源代码都公开在 GitHub 上，用了两种许可。macOS、Windows 和 Linux 的 App，包括 PAM 模块和 Windows Credential Provider，是 Apache 2.0 的开源软件。固件和硬件是 BSL 1.1 的源码公开许可，2030 年转为 Apache 2.0。你可以读全部代码、修改它、自己编译并烧录到自己的设备上。转换之前我们保留的唯一权利是销售与之竞争的硬件。"),
  ("能自己编译、烧录固件吗",
   "能。固件和硬件的源码都是公开的，PCB 上预留了烧录接口，你可以自己编译固件并烧进去。开盖之前先把钥匙重置，因为已配对的钥匙开盖会触发防拆开关。一旦设备跑的是你自己编译的固件，就不再享受保修，也不再收到官方固件更新。"),
  ("和 YubiKey、密码管理器、Touch ID 有什么区别",
   "层次不同，可以一起用。YubiKey 和 passkey 解决的是向网站证明你是谁。immurok 解决的是眼前这台电脑上输密码的麻烦：解锁屏幕、sudo、管理员提示、SSH 和 Git 签名。密码管理器保存你的密码；immurok 在 macOS、Windows、Linux 上都能一碰解锁 1Password 和 Bitwarden，还能把 TOTP 种子存在设备里，这样两步验证的种子就不用躺在桌面 App 中。Touch ID 是苹果自己的传感器，和 Secure Enclave 焊死在一起，第三方用不了，而且 Mac mini 和外接键盘上根本就没有。immurok 是一台独立设备：sudo 和管理员提示走 PAM 这一真实的系统机制，解锁屏幕走另一条单独文档化的辅助路径。"),
  ("有没有给 Mac 用的独立 Touch ID",
   "苹果没有出过。Touch ID 只内置在 MacBook 和带 Touch ID 的妙控键盘里，那把键盘卖 US$149 到 US$199，要求 Apple 芯片的 Mac，而且传感器和键盘绑死，你未必想要那把键盘。单独的 Touch ID 传感器不存在，Touch ID 和 Secure Enclave 焊在一起，第三方也做不出来。immurok 是最接近的东西：一把独立的无线指纹钥匙，放在桌上、挨着你现在用的任何键盘。在 Mac mini、Mac Studio、iMac 或合盖的 MacBook 上，它能解锁屏幕、批准 sudo 和管理员提示、解锁 1Password 和 Bitwarden、给 SSH 和 Git 提交签名。它不是 Touch ID，也不假装是：它是一台单独的设备，有自己的传感器和自己的安全模型，而且 Windows 和 Linux 也能用。"),
  ("需要订阅吗",
   "不需要。没有订阅、没有账号、没有云服务。设备买一次就好。macOS、Windows 和 Linux 的 App 免费，固件更新也免费。就算你从来不把设备连上网，也不会有任何功能停掉，因为它根本不需要联网。"),
  ("怎么重置，丢了怎么办",
   "按住按钮约十秒钟恢复出厂设置。设备会擦掉全部数据，包括配对密钥、所有已录入的指纹和保存的凭据，然后重启回到可配对状态。这个操作不可撤销。如果只是想把钥匙换到另一台电脑而不做完全重置，在 App 里选择解除配对。设备丢了也没人能取出你的指纹：模板不会离开硬件，强行撬开外壳会触发防拆开关，把所有数据擦除并让指示灯常亮红色。每台设备含一年保修。技术支持的联系方式印在用户手册上，App 里也能看到。"),
 ]},

"zh-hant": {
 "code": "zh-Hant",
 "og": "zh_TW",
 "name": "繁體中文",
 "title": "immurok 價格、購買方式與相容性 | 適用於 Mac、Windows、Linux 的無線指紋鑰匙",
 "desc": "immurok 的價格（US$69）、在哪購買、出貨國家、支援的系統、安全性、是否需要訂閱以及重置方法。",
 "lead": "關於 immurok 最常被問到的問題與答案。內容與英文站一致。",
 "cta": "立即購買 · US$69",
 "back": "查看完整英文站點",
 "qa": [
  ("支援哪些電腦和作業系統",
   "macOS 13.0 以上、Windows 10 和 11，以及大多數 Linux 發行版。Mac 版是同時支援 Apple Silicon 和 Intel 的通用版本。Windows 版提供 x64 和 Arm64 原生安裝程式，透過 Credential Provider 整合，所以在鎖定畫面上也能用。Linux 版是用 Rust 寫的常駐程式，整合 PAM 和 polkit，在 Ubuntu、Fedora、Arch、Debian 上測試過，多數其他發行版也能編譯。因為這把鑰匙是獨立的藍牙裝置，不是嵌在筆電裡的感測器，所以在 Mac mini、Mac Studio、iMac、闔蓋的 MacBook、外接鍵盤和桌機上用法完全一樣。一把裝置可以同時綁定兩台電腦，用一根專門的手指在兩者之間切換。"),
  ("支援 Windows Hello 嗎",
   "它不是 Windows Hello 裝置，也不需要是。Windows Hello 是微軟給筆電內建感測器、認證鍵盤和攝影機準備的框架。immurok 走的是另一條路：一個跑在 Windows 登入畫面裡的 Credential Provider，所以觸碰一下就能像 Hello 感測器一樣解開鎖定畫面，而且在沒有 Hello 感測器的桌上型電腦和外接鍵盤上也一樣能用。然後它比 Hello 走得更遠。同一次觸碰還能為 SSH 和 Git 提交簽章、解鎖 1Password 和 Bitwarden、放出 TOTP 驗證碼，同一把鑰匙在 macOS 和 Linux 上也能用。"),
  ("支援 passkey 或 FIDO 嗎",
   "不支援。immurok 不是 FIDO 裝置。它不會作為 passkey 或安全金鑰註冊到網站上，也不能取代 YubiKey。它做的是低一層的事，在你面前這台電腦上：解鎖螢幕、核准 sudo 和系統管理員提示、為 SSH 和 Git 簽章、解鎖密碼管理器、放出 TOTP 驗證碼。登入網站繼續用你的 passkey 或安全金鑰，其餘的交給 immurok，我們很多人兩樣都用。"),
  ("支援 ChromeOS 嗎",
   "不支援。ChromeOS 不給第三方軟體任何參與螢幕解鎖或系統驗證的入口，immurok 沒有地方可以接進去。它支援 macOS 13 及以上、Windows 10 和 11，以及大多數 Linux 發行版。"),
  ("一把鑰匙能在多台電腦上用嗎",
   "能，最多兩台，但同一時間只連線其中一台。鑰匙內部保存兩份獨立的配對，各有各的金鑰，兩台電腦都一直綁著，但任一時刻只和其中一台通訊。你把一根手指錄成「切換指紋」，觸碰它鑰匙就從一台電腦切到另一台，目標電腦自動重新連線。移除其中一台只清掉那一份配對，另一台電腦和已錄入的指紋不受影響。"),
  ("能解鎖 1Password、Bitwarden、LastPass 或 Proton Pass 嗎",
   "四個都可以，在 macOS、Windows 和 Linux 上都支援。密碼管理器跳出解鎖框時，觸碰一下就會填入一段存在鑰匙上的專用密碼並送出，這段密碼與登入密碼分開保存、分開開關。只有在簽章白名單裡的應用程式才能拿到它。"),
  ("能用 USB 連接嗎",
   "只能用來充電。USB-C 埠只給電池充電，不走資料。配對、指紋結果和其他一切都走藍牙 LE，所以電腦需要有藍牙，而工作時鑰匙不佔任何連接埠。"),
  ("電池可以更換嗎",
   "可以。鑰匙用一顆 110 mAh 的可充電鋰電池，透過 USB-C 充電，正常使用一次充電能用一個多月。它是市面上的標準規格，不是客製件，你可以自己換。換之前先取消配對或回復原廠設定：已配對的鑰匙一開蓋就會觸發防拆開關，把資料全部清除。換好電池、闔上外殼，再重新配對。"),
  ("安全性如何，指紋存在哪裡",
   "存在裝置裡，別的地方都沒有。指紋範本儲存在鑰匙內部，比對也在鑰匙內部完成，不會傳到你電腦的硬碟、網路或任何雲端服務。藍牙上傳輸的只是一則用 HMAC 簽章的「比對成功」通知，指紋本身不會出去。配對是裝置和電腦之間直接做 ECDH 金鑰交換。韌體更新都有簽章，安裝前會驗證。沒有帳號、沒有伺服器、沒有遙測，所以全程離線可用，就算我們哪天不在了也照樣能用。"),
  ("是開源的嗎",
   "全部原始碼都公開在 GitHub 上，採用兩種授權。macOS、Windows 和 Linux 的應用程式，包含 PAM 模組和 Windows Credential Provider，是 Apache 2.0 的開源軟體。韌體和硬體採 BSL 1.1 的原始碼公開授權，2030 年轉為 Apache 2.0。你可以讀全部程式碼、修改它、自己編譯並燒錄到自己的裝置上。轉換之前我們保留的唯一權利是販售與之競爭的硬體。"),
  ("能自己編譯、燒錄韌體嗎",
   "能。韌體和硬體的原始碼都是公開的，PCB 上預留了燒錄介面，你可以自己編譯韌體並燒進去。開蓋之前先把鑰匙重置，因為已配對的鑰匙開蓋會觸發防拆開關。一旦裝置跑的是你自己編譯的韌體，就不再享有保固，也不再收到官方韌體更新。"),
  ("和 YubiKey、密碼管理器、Touch ID 有什麼差別",
   "層次不同，可以一起用。YubiKey 和 passkey 解決的是向網站證明你是誰。immurok 解決的是眼前這台電腦上輸入密碼的麻煩：解鎖螢幕、sudo、系統管理員提示、SSH 和 Git 簽章。密碼管理器保存你的密碼；immurok 在 macOS、Windows、Linux 上都能一碰解鎖 1Password 和 Bitwarden，還能把 TOTP 種子存在裝置裡，這樣兩步驟驗證的種子就不用躺在桌面應用程式中。Touch ID 是蘋果自家的感測器，和 Secure Enclave 綁死在一起，第三方用不了，而且 Mac mini 和外接鍵盤上根本就沒有。immurok 是一台獨立裝置：sudo 和系統管理員提示走 PAM 這個真實的系統機制，解鎖螢幕走另一條單獨記錄在文件裡的輔助路徑。"),
  ("有沒有給 Mac 用的獨立 Touch ID",
   "蘋果沒有出過。Touch ID 只內建在 MacBook 和帶 Touch ID 的巧控鍵盤裡，那把鍵盤賣 US$149 到 US$199，需要 Apple 晶片的 Mac，而且感測器和鍵盤綁死，你未必想要那把鍵盤。單獨的 Touch ID 感測器並不存在，Touch ID 和 Secure Enclave 綁在一起，第三方也做不出來。immurok 是最接近的東西：一把獨立的無線指紋鑰匙，放在桌上、挨著你現在用的任何鍵盤。在 Mac mini、Mac Studio、iMac 或闔上的 MacBook 上，它能解鎖螢幕、核准 sudo 和系統管理員提示、解鎖 1Password 和 Bitwarden、為 SSH 和 Git 提交簽章。它不是 Touch ID，也不假裝是：它是一台單獨的裝置，有自己的感測器和自己的安全模型，而且 Windows 和 Linux 也能用。"),
  ("需要訂閱嗎",
   "不需要。沒有訂閱、沒有帳號、沒有雲端服務。裝置買一次就好。macOS、Windows 和 Linux 的應用程式免費，韌體更新也免費。就算你從來不把裝置連上網路，也不會有任何功能停掉，因為它根本不需要連網。"),
  ("怎麼重置，遺失了怎麼辦",
   "按住按鈕約十秒鐘回復原廠設定。裝置會清除全部資料，包括配對金鑰、所有已錄入的指紋和儲存的憑證，然後重新啟動回到可配對狀態。這個動作無法復原。如果只是想把鑰匙換到另一台電腦而不做完全重置，在應用程式裡選擇解除配對。裝置遺失也沒人能取出你的指紋：範本不會離開硬體，強行撬開外殼會觸發防拆開關，把所有資料清除並讓指示燈恆亮紅色。每台裝置含一年保固。技術支援的聯絡方式印在使用手冊上，應用程式裡也看得到。"),
 ]},
}

# ── Page template ───────────────────────────────────────────────────────────

NAV_LOGO = '''      <a href="/" class="nav-logo">
        <img class="nav-logo-wordmark" src="/img/figma/logo-wordmark.png" width="187" height="34" alt="immurok">
        <img class="nav-logo-mark" src="/img/figma/logo-mark.png" width="33" height="28" alt="immurok">
      </a>'''


def tag(slug):
    """hreflang / lang value for a directory. Defaults to the directory name;
    Chinese needs a script subtag (zh-Hans, zh-Hant) that a lowercase URL
    segment cannot carry."""
    return LANGS[slug].get("code", slug)


def locale(slug):
    """og:locale wants language_TERRITORY, which is not the hreflang value."""
    return LANGS[slug].get("og", slug)


def alternates(current):
    """hreflang cluster: every page points at every other, plus x-default."""
    out = ['  <link rel="alternate" hreflang="en" href="%s/">' % SITE,
           '  <link rel="alternate" hreflang="x-default" href="%s/">' % SITE]
    for slug in LANGS:
        out.append('  <link rel="alternate" hreflang="%s" href="%s/%s/">'
                   % (tag(slug), SITE, slug))
    return '\n'.join(out)


def other_langs(current):
    parts = ['<a href="/" hreflang="en" lang="en">English</a>']
    for slug, data in LANGS.items():
        if slug == current:
            continue
        parts.append('<a href="/%s/" hreflang="%s" lang="%s">%s</a>'
                     % (slug, tag(slug), tag(slug), html.escape(data["name"])))
    return ',\n        '.join(parts)


def faq_jsonld(data, code):
    doc = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": "%s/%s/#faq" % (SITE, code),
        "inLanguage": tag(code),
        "url": "%s/%s/" % (SITE, code),
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in data["qa"]
        ],
    }
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return '\n'.join('  ' + line for line in body.split('\n'))


def render(code, data):
    e = html.escape
    items = []
    for q, a in data["qa"]:
        items.append(
            '        <details class="faq-item">\n'
            '          <summary>%s</summary>\n'
            '          <p>%s</p>\n'
            '        </details>' % (e(q), e(a)))

    return '''<!DOCTYPE html>
<html lang="{tag}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <!-- Analytics + consent (shared with every page; see js/analytics.js). -->
  <script src="/js/analytics.js"></script>

  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{site}/{code}/">
{alts}

  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{site}/{code}/">
  <meta property="og:site_name" content="immurok">
  <meta property="og:image" content="{site}/img/og-image.jpg">
  <meta property="og:locale" content="{locale}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@immurok_dev">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{site}/img/og-image.jpg">

  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <meta name="theme-color" content="#1bed43">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">

  <script type="application/ld+json">
{jsonld}
  </script>
</head>
<body>

  <a href="#main-content" class="skip-nav">Skip to content</a>

  <nav class="nav" id="nav">
    <div class="nav-inner">
{navlogo}
      <div class="nav-links">
        <a href="/">{back}</a>
        <a href="/download/">Download</a>
        <a href="/blog/">Blog</a>
      </div>
      <div class="nav-actions">
        <a href="{buy}" class="btn btn-primary btn-sm">{cta}</a>
      </div>
    </div>
  </nav>

  <main id="main-content">
  <section class="section">
    <div class="container-sm">
      <div class="section-header">
        <h1 class="section-title">immurok</h1>
        <p class="section-subtitle">{lead}</p>
      </div>

      <div class="faq-list">
{items}
      </div>

      <p class="qa-langs">
        {langs}
      </p>
    </div>
  </section>
  </main>

  <footer class="footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <img class="footer-logo" src="/img/figma/logo-wordmark.png" width="187" height="34" alt="immurok">
        <p class="footer-tagline">Wireless fingerprint authentication for Mac, Windows &amp; Linux.</p>
      </div>
      <nav class="footer-links" aria-label="Footer">
        <div class="footer-col">
          <h4>Product</h4>
          <a href="/">English site</a>
          <a href="/download/">Download</a>
          <a href="/blog/">Blog</a>
        </div>
        <div class="footer-col">
          <h4>Community</h4>
          <a href="https://discord.gg/beavzPCanZ" target="_blank" rel="noopener">Discord</a>
          <a href="https://github.com/immurok" target="_blank" rel="noopener">GitHub</a>
        </div>
      </nav>
    </div>
    <div class="footer-bottom">
      <span>&copy; 2026 immurok</span>
      <span>Apps: Apache 2.0 &middot; Firmware: BSL 1.1</span>
    </div>
  </footer>

  <script src="/js/main.js"></script>
</body>
</html>
'''.format(code=code, tag=tag(code), locale=locale(code),
           title=e(data["title"]), desc=e(data["desc"]),
           site=SITE, alts=alternates(code), jsonld=faq_jsonld(data, code),
           navlogo=NAV_LOGO, back=e(data["back"]), buy=BUY, cta=e(data["cta"]),
           lead=e(data["lead"]), items='\n'.join(items), langs=other_langs(code))


# Simplified and Traditional Chinese share most characters but not the
# vocabulary, and a mixed table has bitten this project before (the macOS app
# once shipped a Traditional string table with Simplified terms in it). These
# words must never appear in the other variant's answers.
ZH_ONLY = {
    "zh-hans": ["韌體", "軟體", "網路", "螢幕", "裝置", "資料", "保固",
                "群眾募資", "伺服器", "應用程式", "桌上型", "筆電", "金鑰",
                "範本", "簽章", "作業系統", "感測器"],
    "zh-hant": ["固件", "软件", "网络", "屏幕", "设备", "数据", "保修",
                "众筹", "服务器", "台式", "笔记本", "密钥", "模板", "签名",
                "操作系统", "传感器"],
}


def zh_vocabulary_problems():
    """Report any Simplified term that leaked into the Traditional answers, or
    the other way round."""
    problems = []
    for slug, forbidden in ZH_ONLY.items():
        data = LANGS.get(slug)
        if not data:
            continue
        text = ' '.join(q + ' ' + a for q, a in data["qa"])
        text += ' ' + data["title"] + ' ' + data["desc"] + ' ' + data["lead"]
        for word in forbidden:
            if word in text:
                problems.append('%s contains %r, which belongs to the other variant'
                                % (slug, word))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='exit 1 if any generated page is missing or stale')
    args = ap.parse_args()

    mixed = zh_vocabulary_problems()
    if mixed:
        for m in mixed:
            print(m, file=sys.stderr)
        return 1

    stale = []
    for code, data in LANGS.items():
        out = os.path.join(ROOT, code, 'index.html')
        page = render(code, data)
        if args.check:
            current = open(out, encoding='utf-8').read() if os.path.exists(out) else None
            if current != page:
                stale.append(code)
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(page)
        print('wrote %s' % os.path.relpath(out, ROOT))

    if args.check:
        if stale:
            print('stale language pages: %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('all %d language pages up to date, zh vocabulary clean' % len(LANGS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
