#!/usr/bin/env python3
"""Generate the per-language FAQ pages under website/<lang>/index.html.

A third of our search impressions now come from AI assistants, and a large
share of those queries are in languages other than English: price, where to
buy, which countries we ship to, does it work on Linux. Browser translation
does not help there, because the crawler reads the source HTML. So each
language gets a real page with real text.

The pages are deliberately small and static: the same ten answers as the
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
KS = ("https://www.kickstarter.com/projects/immurok/"
      "immurokwireless-fingerprint-auth-key-for-mac-and-linux")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ── Translations ────────────────────────────────────────────────────────────
# Order of the ten answers is identical in every language and matches the
# English homepage. Keep it that way: the hreflang cluster is only useful if
# the pages are genuine equivalents.

LANGS = {
"ja": {
 "og": "ja_JP",
 "name": "日本語",
 "title": "immurok の価格・購入方法・対応OS｜Mac / Windows / Linux 用ワイヤレス指紋キー",
 "desc": "immurok の価格（Kickstarter US$59、通常 US$69）、購入方法、発送国、対応OS、セキュリティ、サブスクの有無、リセット方法をまとめました。",
 "lead": "immurok についてよく聞かれる質問と、その答えです。英語版のサイトと同じ内容を日本語で書いています。",
 "cta": "Kickstarter で支援する",
 "back": "英語版のサイト全体を見る",
 "qa": [
  ("immurok とは何ですか",
   "デスクトップ用の小さなワイヤレス指紋キーです。机の上に置いて Bluetooth LE でパソコンとペアリングし、指を一度触れるだけで画面ロックの解除、sudo や管理者パスワードの承認、SSH と Git のコミット署名、TOTP コードの取り出しができます。Mac mini、Mac Studio、iMac、閉じたまま外部ディスプレイで使う MacBook、外付けキーボード、そしてほとんどの Windows / Linux デスクトップには指紋センサーがありません。そこを埋めるための製品です。"),
  ("価格はいくらですか",
   "Kickstarter では US$59、通常販売価格は US$69 です。買い切りで、サブスクリプションもアカウント料金もありません。送料はこの金額に含まれず、決済時に別途計算されます。早期割引（Early Bird）枠はすでに完売しています。"),
  ("どこで買えますか。いつ発送されますか",
   "現在は Kickstarter で購入できます。キャンペーンは 2026 年 9 月 22 日に終了します。支援者への発送予定は 2026 年 11 月です。ハードウェアは 6 回目の改版で、50 台の試作ロットを製造してテスト済みなので、今回の資金は試作ではなく量産に使われます。キャンペーン終了後はこのサイトで販売します。"),
  ("どの国に発送できますか",
   "発送可能な国の最新リストは Kickstarter の決済画面に表示されます。そちらが正式な情報です。決済画面で国を選ぶと、発送可否と送料が表示されます。送料は支援額に含まれません。輸入関税・付加価値税・通関手数料は受取人のご負担となります。クラウドファンディングでは一般的な条件です。"),
  ("どのパソコンと OS に対応していますか",
   "macOS 13.0 以降、Windows 10 と 11、そして主要な Linux ディストリビューションに対応しています。Mac 版は Apple Silicon と Intel 共通のユニバーサルビルドです。Windows 版は x64 と Arm64 のネイティブインストーラーがあり、Credential Provider として統合されるのでロック画面でも使えます。Linux 版は Rust 製のデーモンで、PAM と polkit に統合されます。Ubuntu、Fedora、Arch、Debian でテストしており、他の多くのディストリビューションでもビルドできます。本体がパソコンとは別の Bluetooth 機器なので、Mac mini でも Mac Studio でも iMac でも、閉じた MacBook でも外付けキーボードでも Windows デスクトップでも、同じように使えます。1 台のキーを 2 台のパソコンに登録し、専用の指で切り替えることもできます。"),
  ("セキュリティはどうなっていますか。指紋データはどこに保存されますか",
   "指紋データは本体の中にだけ保存され、照合も本体の中で行われます。パソコンのディスク、ネットワーク、クラウドには一切届きません。Bluetooth を通るのは HMAC で署名された「照合に成功した」という通知だけで、指紋そのものは流れません。ペアリングは本体とパソコンの間の ECDH 鍵交換です。ファームウェアの更新は署名を検証してから適用されます。アカウントもサーバーもテレメトリもないので、オフラインで完結し、私たちがいなくなっても動き続けます。"),
  ("オープンソースですか",
   "ソースコードはすべて GitHub で公開しています。ライセンスは二つに分かれます。macOS / Windows / Linux のアプリは、PAM モジュールと Windows の Credential Provider を含めて Apache 2.0 のオープンソースです。ファームウェアとハードウェアは BSL 1.1 のソース公開ライセンスで、2030 年に Apache 2.0 に切り替わります。中身をすべて読み、修正し、自分でビルドして書き込むことができます。切り替えまで留保しているのは、競合するハードウェアを販売する権利だけです。"),
  ("YubiKey やパスワードマネージャー、Touch ID とは何が違いますか",
   "レイヤーが違うので、併用できます。YubiKey やパスキーは「Web サイトに対して本人であることを証明する」ものです。immurok は「目の前のパソコンでパスワードを打つ手間をなくす」ものです。画面ロックの解除、sudo、管理者承認、SSH と Git の署名がそれにあたります。パスワードマネージャーはパスワードを保管するものですが、immurok は macOS で 1Password や Bitwarden のロックを指一本で解除でき、TOTP のシードを本体に保存できるので、二要素認証の種をパソコン上のアプリに置かずに済みます。Touch ID は Apple 自身のセンサーで、Secure Enclave と一体化していて他社は利用できず、そもそも Mac mini や外付けキーボードには存在しません。immurok は独立した機器で、sudo と管理者承認は PAM という OS 本来の仕組みを通り、画面ロック解除は別途文書化された経路を使います。"),
  ("サブスクリプションは必要ですか",
   "必要ありません。サブスクリプションもアカウントもクラウドサービスもありません。本体を一度買うだけです。macOS / Windows / Linux のアプリもファームウェア更新も無料です。インターネットに一度もつながなくても、何ひとつ止まりません。"),
  ("リセットの方法は。紛失したらどうなりますか",
   "ボタンを約 10 秒間押し続けると工場出荷状態に戻ります。ペアリング鍵、登録済みの指紋、保存された認証情報がすべて消去され、再ペアリングできる状態で再起動します。この操作は取り消せません。完全な初期化をせずに別のパソコンへ移したい場合は、アプリの「ペアリング解除（Unpair）」を使ってください。紛失しても指紋を取り出されることはありません。テンプレートは本体から外に出ず、ケースをこじ開けると改ざん検知スイッチが働いてすべてのデータを消去し、ランプが赤の点灯のまま停止します。製品には 1 年間の保証が付きます。サポート窓口の連絡先は取扱説明書とアプリに記載しています。"),
 ]},

"es": {
 "og": "es_ES",
 "name": "Español",
 "title": "immurok: precio, dónde comprarlo y compatibilidad | Llave de huella inalámbrica para Mac, Windows y Linux",
 "desc": "Precio de immurok (US$59 en Kickstarter, US$69 al público), dónde comprarlo, a qué países enviamos, sistemas compatibles, seguridad, suscripción y cómo restablecerlo.",
 "lead": "Las preguntas que más nos hacen sobre immurok, respondidas. Es el mismo contenido que la web en inglés.",
 "cta": "Apoyar en Kickstarter",
 "back": "Ver el sitio completo en inglés",
 "qa": [
  ("¿Qué es immurok?",
   "Es una pequeña llave de huella dactilar inalámbrica para ordenadores de escritorio. Se queda en tu mesa y se empareja por Bluetooth LE. Con un toque desbloqueas la pantalla, apruebas peticiones de sudo y de administrador, firmas commits de SSH y Git, y obtienes códigos TOTP. Existe porque la mayoría de los equipos de escritorio no tienen sensor de huella: un Mac mini, un Mac Studio, un iMac, un MacBook cerrado con monitor externo, cualquier teclado externo y casi cualquier PC con Windows o Linux."),
  ("¿Cuánto cuesta immurok?",
   "US$59 en Kickstarter y US$69 al público. Se paga una sola vez. No hay suscripción ni cuota de cuenta. El envío se calcula aparte al finalizar la compra y no está incluido en esos precios. Los tramos early bird de Kickstarter ya se han agotado."),
  ("¿Dónde puedo comprarlo y cuándo se envía?",
   "En Kickstarter, hasta que la campaña termine el 22 de septiembre de 2026. La entrega estimada para los mecenas es noviembre de 2026. El hardware va por su sexta revisión y ya hemos fabricado y probado un lote piloto de 50 unidades, así que la campaña financia la producción en serie, no un prototipo. Cuando termine la campaña lo venderemos desde esta web."),
  ("¿A qué países enviáis?",
   "La lista actualizada de destinos aparece en el proceso de pago de Kickstarter, y esa lista es la que manda. Elige tu país allí y te dirá si podemos enviarte y cuánto cuesta el envío. El envío no está incluido en la aportación. Los aranceles de importación, el IVA y cualquier gasto de aduana corren a cargo de quien recibe el paquete, como es habitual en hardware financiado por crowdfunding."),
  ("¿Con qué ordenadores y sistemas operativos funciona?",
   "macOS 13.0 o posterior, Windows 10 y 11, y la mayoría de distribuciones de Linux. La app de Mac es una única compilación universal para Apple Silicon e Intel. Windows tiene instaladores nativos x64 y Arm64 y se integra como Credential Provider, así que funciona en la pantalla de bloqueo. Linux es un demonio en Rust con integración PAM y polkit, probado en Ubuntu, Fedora, Arch y Debian, y compila en casi cualquier otra distribución. Como la llave es un dispositivo Bluetooth independiente y no un sensor incrustado en un portátil, funciona igual en un Mac mini, un Mac Studio, un iMac, un MacBook cerrado, un teclado externo o un PC de sobremesa. Una misma llave puede quedar vinculada a dos ordenadores a la vez y cambiar entre ellos con una huella dedicada."),
  ("¿Qué nivel de seguridad tiene? ¿Dónde se guardan mis huellas?",
   "En el dispositivo, y en ningún otro sitio. Las plantillas de huella se guardan y se comparan dentro de la propia llave. Nunca llegan al disco de tu ordenador, ni a la red, ni a ningún servicio en la nube. Por Bluetooth solo viaja una notificación firmada con HMAC que dice que la huella coincide, nunca la huella. El emparejamiento es un intercambio ECDH directo entre el dispositivo y tu máquina. Las actualizaciones de firmware van firmadas y se verifican antes de instalarse. No hay cuenta, ni servidor, ni telemetría: todo funciona sin conexión y seguiría funcionando si nosotros desapareciéramos."),
  ("¿Es de código abierto?",
   "Todo el código fuente es público en GitHub, con dos licencias distintas. Las apps de macOS, Windows y Linux, incluidos los módulos PAM y el Credential Provider de Windows, son código abierto bajo Apache 2.0. El firmware y el hardware son de código disponible bajo BSL 1.1 y pasan a Apache 2.0 en 2030. Puedes leerlo todo, modificarlo, compilarlo y grabarlo en tu propia unidad. El único derecho que nos reservamos hasta la conversión es vender hardware competidor."),
  ("¿En qué se diferencia de una YubiKey, un gestor de contraseñas o Touch ID?",
   "Son capas distintas y se complementan. Una YubiKey y las passkeys demuestran quién eres ante una web. immurok elimina la fricción de la contraseña en la máquina que tienes delante: desbloqueo de pantalla, sudo, peticiones de administrador, firma de SSH y Git. Un gestor de contraseñas guarda tus contraseñas; immurok desbloquea 1Password y Bitwarden con un toque en macOS y guarda las semillas TOTP en el propio dispositivo, para que tus códigos de doble factor no vivan en una app del escritorio. Touch ID es el sensor propio de Apple, fundido con el Secure Enclave, cerrado a terceros, y sencillamente no existe en un Mac mini ni en un teclado externo. immurok es un dispositivo independiente: sudo y las peticiones de administrador pasan por PAM, un mecanismo real del sistema, y el desbloqueo de pantalla usa una ruta auxiliar documentada aparte."),
  ("¿Hace falta una suscripción?",
   "No. Ni suscripción, ni cuenta, ni servicio en la nube. Pagas una vez por el dispositivo. Las apps de macOS, Windows y Linux son gratuitas, y las actualizaciones de firmware también. Nada deja de funcionar aunque no conectes nunca el dispositivo a internet, porque no lo necesita."),
  ("¿Cómo se restablece? ¿Y si lo pierdo?",
   "Mantén pulsado el botón unos diez segundos para restablecerlo de fábrica. El dispositivo borra todo: claves de emparejamiento, todas las huellas registradas y las credenciales guardadas, y se reinicia listo para emparejarse otra vez. No se puede deshacer. Para pasar la llave a otro ordenador sin un borrado completo, usa Desemparejar en la app. Si la pierdes, nadie puede extraer tus huellas: las plantillas nunca salen del hardware y forzar la carcasa activa un interruptor antimanipulación que lo borra todo y deja la luz en rojo fijo. Cada unidad incluye un año de garantía. La dirección de soporte viene en el manual de usuario y aparece en la app."),
 ]},

"pt": {
 "og": "pt_BR",
 "name": "Português",
 "title": "immurok: preço, onde comprar e compatibilidade | Chave de impressão digital sem fio para Mac, Windows e Linux",
 "desc": "Preço do immurok (US$59 no Kickstarter, US$69 no varejo), onde comprar, para quais países enviamos, sistemas compatíveis, segurança, assinatura e como redefinir.",
 "lead": "As perguntas que mais recebemos sobre o immurok, respondidas. É o mesmo conteúdo do site em inglês.",
 "cta": "Apoiar no Kickstarter",
 "back": "Ver o site completo em inglês",
 "qa": [
  ("O que é o immurok?",
   "É uma pequena chave de impressão digital sem fio para computadores de mesa. Ela fica na sua mesa e pareia por Bluetooth LE. Com um toque você desbloqueia a tela, aprova pedidos de sudo e de administrador, assina commits de SSH e Git e obtém códigos TOTP. Ela existe porque a maioria dos computadores de mesa não tem sensor de digital: um Mac mini, um Mac Studio, um iMac, um MacBook fechado ligado a um monitor externo, qualquer teclado externo e quase todo PC com Windows ou Linux."),
  ("Quanto custa o immurok?",
   "US$59 no Kickstarter e US$69 no varejo. É pagamento único. Não há assinatura nem taxa de conta. O frete é calculado à parte no checkout e não está incluído nesses valores. Os lotes early bird do Kickstarter já se esgotaram."),
  ("Onde posso comprar e quando é enviado?",
   "No Kickstarter, até a campanha terminar em 22 de setembro de 2026. A entrega estimada para os apoiadores é novembro de 2026. O hardware está na sexta revisão e um lote piloto de 50 unidades já foi produzido e testado, então a campanha financia a produção em série, não um protótipo. Depois da campanha, passamos a vender por este site."),
  ("Para quais países vocês enviam?",
   "A lista atual de destinos aparece no checkout do Kickstarter, e é ela que vale. Escolha seu país lá e o sistema informa se conseguimos enviar e quanto custa o frete. O frete não está incluído no valor do apoio. Impostos de importação, ICMS e taxas alfandegárias são de responsabilidade de quem recebe, como é comum em hardware financiado por crowdfunding."),
  ("Com quais computadores e sistemas operacionais funciona?",
   "macOS 13.0 ou mais recente, Windows 10 e 11, e a maioria das distribuições Linux. O app do Mac é uma única build universal para Apple Silicon e Intel. O Windows tem instaladores nativos x64 e Arm64 e se integra como Credential Provider, então funciona na tela de bloqueio. O Linux é um daemon em Rust com integração PAM e polkit, testado em Ubuntu, Fedora, Arch e Debian, e compila na maioria das outras distribuições. Como a chave é um dispositivo Bluetooth separado, e não um sensor embutido no notebook, ela funciona igual em um Mac mini, um Mac Studio, um iMac, um MacBook fechado, um teclado externo ou um PC de mesa. Uma mesma chave pode ficar vinculada a dois computadores ao mesmo tempo e alternar entre eles com uma digital dedicada."),
  ("Qual é o nível de segurança? Onde ficam minhas digitais?",
   "No dispositivo, e em nenhum outro lugar. Os templates de digital são armazenados e comparados dentro da própria chave. Eles nunca chegam ao disco do seu computador, à rede ou a qualquer serviço em nuvem. Pelo Bluetooth trafega apenas uma notificação assinada com HMAC dizendo que a digital bateu, nunca a digital em si. O pareamento é uma troca ECDH direta entre o dispositivo e a sua máquina. As atualizações de firmware são assinadas e verificadas antes de serem instaladas. Não há conta, servidor nem telemetria: tudo funciona offline e continuaria funcionando se nós desaparecêssemos."),
  ("É código aberto?",
   "Todo o código-fonte é público no GitHub, sob duas licenças diferentes. Os apps de macOS, Windows e Linux, incluindo os módulos PAM e o Credential Provider do Windows, são código aberto sob Apache 2.0. O firmware e o hardware são de código disponível sob BSL 1.1 e passam para Apache 2.0 em 2030. Você pode ler tudo, modificar, compilar e gravar na sua própria unidade. O único direito reservado até a conversão é vender hardware concorrente."),
  ("Qual a diferença para uma YubiKey, um gerenciador de senhas ou o Touch ID?",
   "São camadas diferentes e funcionam juntas. Uma YubiKey e as passkeys provam quem você é para um site. O immurok tira o atrito da senha na máquina à sua frente: desbloqueio de tela, sudo, pedidos de administrador, assinatura de SSH e Git. Um gerenciador de senhas guarda suas senhas; o immurok destrava o 1Password e o Bitwarden com um toque no macOS e guarda as sementes TOTP no próprio dispositivo, para que seus códigos de dois fatores não fiquem em um app do desktop. O Touch ID é o sensor da própria Apple, fundido ao Secure Enclave, fechado para terceiros, e simplesmente não existe em um Mac mini ou em um teclado externo. O immurok é um dispositivo independente: sudo e pedidos de administrador passam pelo PAM, um mecanismo real do sistema, e o desbloqueio de tela usa um caminho auxiliar documentado à parte."),
  ("Precisa de assinatura?",
   "Não. Sem assinatura, sem conta, sem serviço em nuvem. Você paga uma vez pelo dispositivo. Os apps de macOS, Windows e Linux são gratuitos, e as atualizações de firmware também. Nada para de funcionar se você nunca conectar o dispositivo à internet, porque ele não precisa disso."),
  ("Como redefinir? E se eu perder?",
   "Segure o botão por cerca de dez segundos para restaurar de fábrica. O dispositivo apaga tudo: chaves de pareamento, todas as digitais cadastradas e as credenciais armazenadas, e reinicia pronto para parear de novo. Isso não pode ser desfeito. Para passar a chave para outro computador sem apagar tudo, use Desparear no app. Se você perder, ninguém consegue extrair suas digitais: os templates nunca saem do hardware, e forçar a carcaça aciona uma chave antiviolação que apaga tudo e deixa a luz em vermelho fixo. Cada unidade inclui um ano de garantia. O endereço de suporte está no manual do usuário e aparece no app."),
 ]},

"de": {
 "og": "de_DE",
 "name": "Deutsch",
 "title": "immurok: Preis, Kauf und Kompatibilität | Kabelloser Fingerabdruck-Key für Mac, Windows und Linux",
 "desc": "immurok Preis (US$59 auf Kickstarter, US$69 im Handel), wo man ihn kauft, Versandländer, unterstützte Systeme, Sicherheit, Abo und Zurücksetzen.",
 "lead": "Die Fragen, die uns am häufigsten zu immurok gestellt werden, hier beantwortet. Inhaltlich dasselbe wie auf der englischen Seite.",
 "cta": "Auf Kickstarter unterstützen",
 "back": "Die vollständige Seite auf Englisch ansehen",
 "qa": [
  ("Was ist immurok?",
   "Ein kleiner kabelloser Fingerabdruck-Key für Desktop-Rechner. Er liegt auf dem Schreibtisch und wird per Bluetooth LE gekoppelt. Eine Berührung entsperrt den Bildschirm, bestätigt sudo- und Administratorabfragen, signiert SSH- und Git-Commits und gibt TOTP-Codes frei. Es gibt ihn, weil die meisten Desktop-Rechner keinen Fingerabdrucksensor haben: ein Mac mini, ein Mac Studio, ein iMac, ein zugeklappter MacBook am externen Monitor, jede externe Tastatur und praktisch jeder Windows- oder Linux-Desktop."),
  ("Was kostet immurok?",
   "US$59 auf Kickstarter, US$69 im regulären Verkauf. Einmalzahlung. Kein Abo, keine Kontogebühr. Der Versand wird separat an der Kasse berechnet und ist in diesen Preisen nicht enthalten. Die Early-Bird-Kontingente auf Kickstarter sind bereits ausverkauft."),
  ("Wo kann ich ihn kaufen und wann wird geliefert?",
   "Auf Kickstarter, bis die Kampagne am 22. September 2026 endet. Die geschätzte Lieferung für Unterstützer ist November 2026. Die Hardware ist in der sechsten Revision, und eine Pilotserie von 50 Stück ist gebaut und geprüft. Die Kampagne finanziert also die Serienfertigung, keinen Prototyp. Nach der Kampagne verkaufen wir über diese Website."),
  ("In welche Länder versendet ihr?",
   "Die aktuelle Liste der Versandziele steht im Kickstarter-Checkout, und diese Liste ist maßgeblich. Wählen Sie dort Ihr Land aus, dann sehen Sie, ob wir liefern können und was der Versand kostet. Der Versand ist im Unterstützungsbetrag nicht enthalten. Einfuhrzölle, Mehrwertsteuer und Zollgebühren trägt die empfangende Person, wie bei crowdfinanzierter Hardware üblich."),
  ("Mit welchen Rechnern und Betriebssystemen funktioniert er?",
   "macOS 13.0 oder neuer, Windows 10 und 11 sowie die meisten Linux-Distributionen. Die Mac-App ist ein einziges Universal-Build für Apple Silicon und Intel. Für Windows gibt es native x64- und Arm64-Installer, und die Integration läuft über einen Credential Provider, funktioniert also auf dem Sperrbildschirm. Linux ist ein Rust-Daemon mit PAM- und polkit-Integration, getestet auf Ubuntu, Fedora, Arch und Debian, und er baut auf den meisten anderen Distributionen. Weil der Key ein eigenständiges Bluetooth-Gerät ist und kein im Laptop verbauter Sensor, funktioniert er auf einem Mac mini, einem Mac Studio, einem iMac, einem zugeklappten MacBook, einer externen Tastatur oder einem Desktop-PC gleich gut. Ein Key kann gleichzeitig an zwei Rechner gebunden sein; mit einem eigens dafür angelernten Finger wechselt man zwischen ihnen."),
  ("Wie sicher ist er? Wo liegen meine Fingerabdrücke?",
   "Auf dem Gerät, und sonst nirgends. Die Fingerabdruck-Templates werden auf dem Key selbst gespeichert und dort verglichen. Sie erreichen weder die Festplatte Ihres Rechners noch das Netzwerk noch irgendeinen Cloud-Dienst. Über Bluetooth geht nur eine HMAC-signierte Meldung, dass der Abdruck gepasst hat, niemals der Abdruck selbst. Das Pairing ist ein direkter ECDH-Austausch zwischen Gerät und Rechner. Firmware-Updates sind signiert und werden vor der Installation geprüft. Es gibt kein Konto, keinen Server und keine Telemetrie: alles läuft offline und würde weiterlaufen, wenn es uns nicht mehr gäbe."),
  ("Ist er Open Source?",
   "Der gesamte Quellcode ist auf GitHub öffentlich, unter zwei verschiedenen Lizenzen. Die Apps für macOS, Windows und Linux, einschließlich der PAM-Module und des Windows Credential Provider, sind Open Source unter Apache 2.0. Firmware und Hardware sind source-available unter BSL 1.1 und wechseln 2030 zu Apache 2.0. Sie können alles lesen, ändern, selbst bauen und auf Ihr eigenes Gerät flashen. Bis zur Umstellung behalten wir uns nur ein Recht vor: konkurrierende Hardware zu verkaufen."),
  ("Worin unterscheidet er sich von einem YubiKey, einem Passwortmanager oder Touch ID?",
   "Andere Ebene, und sie ergänzen sich. Ein YubiKey und Passkeys weisen gegenüber einer Website nach, wer Sie sind. immurok nimmt die Passworthürde an dem Rechner weg, vor dem Sie sitzen: Bildschirm entsperren, sudo, Administratorabfragen, SSH- und Git-Signaturen. Ein Passwortmanager speichert Ihre Passwörter; immurok entsperrt 1Password und Bitwarden unter macOS mit einer Berührung und hält TOTP-Seeds auf dem Gerät, damit Ihre Zwei-Faktor-Geheimnisse nicht in einer Desktop-App liegen. Touch ID ist Apples eigener Sensor, fest mit der Secure Enclave verbunden, für Dritte verschlossen, und auf einem Mac mini oder einer externen Tastatur schlicht nicht vorhanden. immurok ist ein eigenständiges Gerät: sudo und Administratorabfragen laufen über PAM, einen echten Systemmechanismus, und das Entsperren des Bildschirms nutzt einen separat dokumentierten Hilfsweg."),
  ("Brauche ich ein Abo?",
   "Nein. Kein Abo, kein Konto, kein Cloud-Dienst. Sie zahlen einmal für das Gerät. Die Apps für macOS, Windows und Linux sind kostenlos, Firmware-Updates ebenfalls. Nichts hört auf zu funktionieren, wenn Sie das Gerät nie mit dem Internet verbinden, denn das braucht es nicht."),
  ("Wie setze ich ihn zurück, und was ist, wenn ich ihn verliere?",
   "Halten Sie die Taste etwa zehn Sekunden gedrückt, um auf Werkseinstellungen zurückzusetzen. Das Gerät löscht alles: Pairing-Schlüssel, sämtliche angelernten Fingerabdrücke und gespeicherte Zugangsdaten, und startet bereit zum erneuten Koppeln. Das lässt sich nicht rückgängig machen. Um den Key ohne vollständiges Zurücksetzen an einen anderen Rechner zu geben, wählen Sie in der App Entkoppeln. Wenn Sie ihn verlieren, kann niemand Ihre Fingerabdrücke auslesen: die Templates verlassen die Hardware nie, und wer das Gehäuse aufbricht, löst einen Tamper-Schalter aus, der alles löscht und die Leuchte dauerhaft rot stehen lässt. Jedes Gerät hat ein Jahr Garantie. Die Support-Adresse steht im Handbuch und in der App."),
 ]},

"ko": {
 "og": "ko_KR",
 "name": "한국어",
 "title": "immurok 가격·구매·호환성 | Mac, Windows, Linux용 무선 지문 키",
 "desc": "immurok 가격(킥스타터 US$59, 정가 US$69), 구매 방법, 배송 국가, 지원 OS, 보안, 구독 여부, 초기화 방법을 정리했습니다.",
 "lead": "immurok에 대해 가장 많이 받는 질문과 답변입니다. 영문 사이트와 같은 내용입니다.",
 "cta": "킥스타터에서 후원하기",
 "back": "영문 사이트 전체 보기",
 "qa": [
  ("immurok은 무엇인가요?",
   "데스크톱용 소형 무선 지문 키입니다. 책상 위에 두고 블루투스 LE로 컴퓨터와 페어링하며, 한 번 터치하면 화면 잠금 해제, sudo 및 관리자 권한 승인, SSH와 Git 커밋 서명, TOTP 코드 인출이 됩니다. Mac mini, Mac Studio, iMac, 덮개를 닫고 외부 모니터로 쓰는 MacBook, 외장 키보드, 그리고 대부분의 Windows와 Linux 데스크톱에는 지문 센서가 없습니다. 그 빈자리를 메우는 제품입니다."),
  ("가격은 얼마인가요?",
   "킥스타터에서 US$59, 정가는 US$69입니다. 한 번만 결제하면 되고 구독료나 계정 요금이 없습니다. 배송비는 이 금액에 포함되지 않으며 결제 단계에서 별도로 계산됩니다. 킥스타터 얼리버드 물량은 이미 모두 소진되었습니다."),
  ("어디서 살 수 있고 언제 배송되나요?",
   "현재는 킥스타터에서 구매할 수 있으며, 캠페인은 2026년 9월 22일에 종료됩니다. 후원자 예상 배송 시점은 2026년 11월입니다. 하드웨어는 6차 리비전이고 50대 파일럿 물량을 생산해 시험을 마쳤기 때문에, 이번 자금은 시제품이 아니라 양산에 쓰입니다. 캠페인이 끝나면 이 사이트에서 판매합니다."),
  ("어느 나라로 배송되나요?",
   "배송 가능한 국가의 최신 목록은 킥스타터 결제 화면에 표시되며, 그 목록이 기준입니다. 결제 화면에서 국가를 선택하면 배송 가능 여부와 배송비가 나옵니다. 배송비는 후원 금액에 포함되지 않습니다. 수입 관세, 부가세, 통관 수수료는 수령인 부담이며, 크라우드펀딩 하드웨어에서는 일반적인 조건입니다."),
  ("어떤 컴퓨터와 운영체제에서 쓸 수 있나요?",
   "macOS 13.0 이상, Windows 10과 11, 그리고 대부분의 Linux 배포판을 지원합니다. Mac 앱은 Apple Silicon과 Intel을 함께 지원하는 단일 유니버설 빌드입니다. Windows는 x64와 Arm64 네이티브 설치 파일을 제공하고 Credential Provider로 통합되므로 잠금 화면에서도 동작합니다. Linux는 Rust로 만든 데몬이며 PAM과 polkit에 통합됩니다. Ubuntu, Fedora, Arch, Debian에서 검증했고 다른 배포판에서도 대부분 빌드됩니다. 키가 노트북에 내장된 센서가 아니라 별도의 블루투스 기기이기 때문에 Mac mini, Mac Studio, iMac, 덮은 MacBook, 외장 키보드, 데스크톱 PC 모두 동일하게 동작합니다. 키 하나를 두 대의 컴퓨터에 동시에 등록해 두고 전용 지문으로 전환할 수도 있습니다."),
  ("보안은 어떤가요? 지문은 어디에 저장되나요?",
   "기기 안에만 저장되고, 대조도 기기 안에서 이루어집니다. 컴퓨터의 디스크나 네트워크, 클라우드 서비스에는 전혀 전달되지 않습니다. 블루투스로 오가는 것은 HMAC로 서명된 일치 알림뿐이며 지문 자체는 나가지 않습니다. 페어링은 기기와 컴퓨터 사이의 직접 ECDH 교환입니다. 펌웨어 업데이트는 서명되어 있고 설치 전에 검증합니다. 계정도 서버도 텔레메트리도 없으므로 오프라인에서 완결되며, 저희가 사라져도 계속 동작합니다."),
  ("오픈소스인가요?",
   "모든 소스 코드가 GitHub에 공개되어 있고 라이선스는 두 가지입니다. macOS, Windows, Linux 앱은 PAM 모듈과 Windows Credential Provider를 포함해 Apache 2.0 오픈소스입니다. 펌웨어와 하드웨어는 BSL 1.1의 소스 공개 라이선스이며 2030년에 Apache 2.0으로 전환됩니다. 전부 읽고 수정하고 직접 빌드해 자기 기기에 써 넣을 수 있습니다. 전환 전까지 유보하는 권리는 경쟁 하드웨어를 판매하는 것뿐입니다."),
  ("YubiKey, 비밀번호 관리자, Touch ID와는 어떻게 다른가요?",
   "계층이 달라서 함께 쓸 수 있습니다. YubiKey와 패스키는 웹사이트에 대해 본인임을 증명합니다. immurok은 눈앞의 컴퓨터에서 비밀번호를 입력하는 번거로움을 없앱니다. 화면 잠금 해제, sudo, 관리자 승인, SSH와 Git 서명이 그렇습니다. 비밀번호 관리자는 비밀번호를 보관하지만, immurok은 macOS에서 1Password와 Bitwarden을 터치 한 번으로 잠금 해제하고 TOTP 시드를 기기 안에 보관해 2단계 인증 시드가 데스크톱 앱에 남지 않게 합니다. Touch ID는 Apple 자체 센서로 Secure Enclave와 결합되어 있어 서드파티가 쓸 수 없고, Mac mini나 외장 키보드에는 아예 없습니다. immurok은 독립된 기기이며, sudo와 관리자 승인은 PAM이라는 실제 시스템 메커니즘을 통하고 화면 잠금 해제는 별도로 문서화된 경로를 사용합니다."),
  ("구독이 필요한가요?",
   "필요 없습니다. 구독도, 계정도, 클라우드 서비스도 없습니다. 기기 값을 한 번만 내면 됩니다. macOS, Windows, Linux 앱과 펌웨어 업데이트 모두 무료입니다. 기기를 인터넷에 한 번도 연결하지 않아도 아무것도 멈추지 않습니다. 연결할 필요가 없기 때문입니다."),
  ("초기화는 어떻게 하나요? 분실하면 어떻게 되나요?",
   "버튼을 약 10초간 누르고 있으면 공장 초기화가 됩니다. 페어링 키, 등록된 모든 지문, 저장된 자격 증명이 모두 지워지고 다시 페어링할 수 있는 상태로 재시작합니다. 되돌릴 수 없습니다. 완전 초기화 없이 다른 컴퓨터로 옮기려면 앱에서 페어링 해제를 선택하세요. 분실하더라도 지문을 빼낼 수는 없습니다. 템플릿은 하드웨어를 벗어나지 않으며, 케이스를 강제로 열면 변조 감지 스위치가 작동해 모든 데이터를 지우고 표시등이 빨간색으로 고정됩니다. 모든 제품에 1년 보증이 포함됩니다. 지원 연락처는 사용 설명서와 앱에 안내되어 있습니다."),
 ]},

"ru": {
 "og": "ru_RU",
 "name": "Русский",
 "title": "immurok: цена, где купить и совместимость | Беспроводной ключ по отпечатку для Mac, Windows и Linux",
 "desc": "Цена immurok (US$59 на Kickstarter, US$69 в рознице), где купить, в какие страны отправляем, поддерживаемые системы, безопасность, подписка и сброс.",
 "lead": "Вопросы, которые нам задают чаще всего, и ответы на них. То же содержание, что и на англоязычном сайте.",
 "cta": "Поддержать на Kickstarter",
 "back": "Открыть полный сайт на английском",
 "qa": [
  ("Что такое immurok?",
   "Небольшой беспроводной ключ с датчиком отпечатка для настольных компьютеров. Он лежит на столе и подключается по Bluetooth LE. Одно касание разблокирует экран, подтверждает запросы sudo и прав администратора, подписывает коммиты SSH и Git и выдаёт коды TOTP. Он нужен потому, что у большинства настольных машин датчика отпечатка нет: Mac mini, Mac Studio, iMac, закрытый MacBook с внешним монитором, любая внешняя клавиатура и почти любой настольный ПК с Windows или Linux."),
  ("Сколько стоит immurok?",
   "US$59 на Kickstarter и US$69 в рознице. Оплата разовая. Никакой подписки и платы за аккаунт. Доставка считается отдельно при оформлении и в эти суммы не входит. Ранние лоты early bird на Kickstarter уже закончились."),
  ("Где купить и когда отправят?",
   "На Kickstarter, пока кампания не закончится 22 сентября 2026 года. Ориентировочная отправка бэкерам: ноябрь 2026 года. Железо в шестой ревизии, пилотная партия из 50 штук собрана и протестирована, так что кампания финансирует серийное производство, а не прототип. После кампании продажи пойдут через этот сайт."),
  ("В какие страны вы отправляете?",
   "Актуальный список стран показывается при оформлении заказа на Kickstarter, и именно он является основным. Выберите там свою страну, и система покажет, можем ли мы отправить и сколько будет стоить доставка. Доставка не входит в сумму поддержки. Ввозные пошлины, НДС и таможенные сборы оплачивает получатель, как обычно бывает с краудфандинговым оборудованием."),
  ("С какими компьютерами и системами он работает?",
   "macOS 13.0 и новее, Windows 10 и 11, а также большинство дистрибутивов Linux. Приложение для Mac собрано единым универсальным бинарником для Apple Silicon и Intel. Для Windows есть нативные установщики x64 и Arm64, интеграция идёт через Credential Provider, поэтому работает и на экране блокировки. Для Linux это демон на Rust с интеграцией в PAM и polkit, проверенный на Ubuntu, Fedora, Arch и Debian и собирающийся на большинстве других дистрибутивов. Поскольку ключ — отдельное Bluetooth-устройство, а не встроенный в ноутбук датчик, он одинаково работает с Mac mini, Mac Studio, iMac, закрытым MacBook, внешней клавиатурой и настольным ПК. Один ключ можно привязать сразу к двум компьютерам и переключаться между ними отдельным пальцем."),
  ("Насколько это безопасно? Где хранятся отпечатки?",
   "На самом устройстве и больше нигде. Шаблоны отпечатков хранятся и сравниваются внутри ключа. Они не попадают ни на диск компьютера, ни в сеть, ни в облако. По Bluetooth передаётся только подписанное HMAC уведомление о совпадении, но не сам отпечаток. Сопряжение — прямой обмен ECDH между устройством и вашей машиной. Обновления прошивки подписаны и проверяются перед установкой. Нет аккаунта, нет сервера, нет телеметрии: всё работает офлайн и продолжит работать, даже если нас не станет."),
  ("Это открытый исходный код?",
   "Весь исходный код опубликован на GitHub под двумя разными лицензиями. Приложения для macOS, Windows и Linux, включая модули PAM и Credential Provider для Windows, открыты под Apache 2.0. Прошивка и аппаратная часть доступны по BSL 1.1 и перейдут на Apache 2.0 в 2030 году. Всё можно прочитать, изменить, собрать и прошить в собственное устройство. До перехода мы оставляем за собой единственное право: продавать конкурирующее оборудование."),
  ("Чем это отличается от YubiKey, менеджера паролей или Touch ID?",
   "Это другой уровень, и они дополняют друг друга. YubiKey и passkeys доказывают сайту, кто вы. immurok убирает возню с паролем на той машине, что перед вами: разблокировка экрана, sudo, запросы администратора, подпись SSH и Git. Менеджер паролей хранит пароли; immurok разблокирует 1Password и Bitwarden одним касанием на macOS и держит секреты TOTP на самом устройстве, чтобы сиды двухфакторной аутентификации не лежали в настольном приложении. Touch ID — собственный датчик Apple, сращённый с Secure Enclave, закрытый для сторонних разработчиков, и на Mac mini или внешней клавиатуре его просто нет. immurok — независимое устройство: sudo и запросы администратора идут через PAM, реальный системный механизм, а разблокировка экрана использует отдельно задокументированный путь."),
  ("Нужна ли подписка?",
   "Нет. Ни подписки, ни аккаунта, ни облачного сервиса. Вы платите за устройство один раз. Приложения для macOS, Windows и Linux бесплатны, обновления прошивки тоже. Ничего не перестанет работать, даже если вы никогда не подключите устройство к интернету, потому что ему это не нужно."),
  ("Как сбросить и что делать при потере?",
   "Удерживайте кнопку около десяти секунд для сброса к заводским настройкам. Устройство стирает всё: ключи сопряжения, все записанные отпечатки и сохранённые учётные данные, и перезапускается готовым к новому сопряжению. Отменить это нельзя. Чтобы передать ключ на другой компьютер без полного сброса, выберите в приложении «Отвязать». Если ключ потерян, извлечь отпечатки из него невозможно: шаблоны не покидают железо, а вскрытие корпуса срабатывает как защита от вмешательства, стирает всё и оставляет индикатор гореть красным. На каждое устройство даётся год гарантии. Адрес поддержки указан в руководстве пользователя и в приложении."),
 ]},

"nl": {
 "og": "nl_NL",
 "name": "Nederlands",
 "title": "immurok: prijs, waar te koop en compatibiliteit | Draadloze vingerafdruksleutel voor Mac, Windows en Linux",
 "desc": "Prijs van immurok (US$59 op Kickstarter, US$69 in de winkel), waar te koop, verzendlanden, ondersteunde systemen, beveiliging, abonnement en resetten.",
 "lead": "De vragen die we het vaakst krijgen over immurok, beantwoord. Zelfde inhoud als de Engelse site.",
 "cta": "Steun op Kickstarter",
 "back": "Bekijk de volledige site in het Engels",
 "qa": [
  ("Wat is immurok?",
   "Een kleine draadloze vingerafdruksleutel voor desktopcomputers. Hij ligt op je bureau en koppelt via Bluetooth LE. Eén aanraking ontgrendelt je scherm, keurt sudo- en beheerdersvragen goed, ondertekent SSH- en Git-commits en geeft TOTP-codes vrij. Hij bestaat omdat de meeste desktops geen vingerafdruksensor hebben: een Mac mini, een Mac Studio, een iMac, een dichtgeklapte MacBook op een externe monitor, elk extern toetsenbord en vrijwel elke Windows- of Linux-desktop."),
  ("Wat kost immurok?",
   "US$59 op Kickstarter, US$69 in de reguliere verkoop. Je betaalt één keer. Geen abonnement en geen accountkosten. Verzending wordt apart berekend bij het afrekenen en zit niet in die prijzen. De early-bird-tranches op Kickstarter zijn uitverkocht."),
  ("Waar kan ik hem kopen en wanneer wordt hij verstuurd?",
   "Op Kickstarter, tot de campagne op 22 september 2026 afloopt. De verwachte levering voor backers is november 2026. De hardware zit in de zesde revisie en een pilotserie van 50 stuks is gebouwd en getest, dus de campagne financiert serieproductie en geen prototype. Na de campagne verkopen we via deze site."),
  ("Naar welke landen verzenden jullie?",
   "De actuele lijst met bestemmingen staat in de Kickstarter-checkout, en die lijst is leidend. Kies daar je land en je ziet of we kunnen verzenden en wat verzending kost. Verzending zit niet in het steunbedrag. Invoerrechten, btw en douanekosten zijn voor de ontvanger, zoals gebruikelijk bij crowdfunded hardware."),
  ("Met welke computers en besturingssystemen werkt hij?",
   "macOS 13.0 of nieuwer, Windows 10 en 11, en de meeste Linux-distributies. De Mac-app is één universele build voor Apple Silicon en Intel. Windows heeft native x64- en Arm64-installers en integreert via een Credential Provider, dus hij werkt op het vergrendelscherm. Linux is een daemon in Rust met PAM- en polkit-integratie, getest op Ubuntu, Fedora, Arch en Debian, en hij bouwt op de meeste andere distributies. Omdat de sleutel een los Bluetooth-apparaat is en geen sensor in een laptop, werkt hij hetzelfde op een Mac mini, een Mac Studio, een iMac, een dichtgeklapte MacBook, een extern toetsenbord of een desktop-pc. Eén sleutel kan aan twee computers tegelijk gekoppeld zijn en met een aparte vinger schakel je ertussen."),
  ("Hoe veilig is het? Waar staan mijn vingerafdrukken?",
   "Op het apparaat, en nergens anders. De vingerafdruksjablonen worden op de sleutel zelf opgeslagen en daar vergeleken. Ze bereiken nooit de schijf van je computer, het netwerk of een clouddienst. Over Bluetooth gaat alleen een met HMAC ondertekende melding dat de afdruk klopte, nooit de afdruk zelf. Koppelen is een directe ECDH-uitwisseling tussen apparaat en computer. Firmware-updates zijn ondertekend en worden voor installatie geverifieerd. Er is geen account, geen server en geen telemetrie: alles werkt offline en zou blijven werken als wij verdwijnen."),
  ("Is het open source?",
   "Alle broncode staat publiek op GitHub, onder twee verschillende licenties. De apps voor macOS, Windows en Linux, inclusief de PAM-modules en de Windows Credential Provider, zijn open source onder Apache 2.0. Firmware en hardware zijn source-available onder BSL 1.1 en gaan in 2030 over naar Apache 2.0. Je kunt alles lezen, aanpassen, zelf bouwen en op je eigen apparaat flashen. Het enige recht dat we tot die overgang voorbehouden is het verkopen van concurrerende hardware."),
  ("Wat is het verschil met een YubiKey, een wachtwoordmanager of Touch ID?",
   "Andere laag, en ze vullen elkaar aan. Een YubiKey en passkeys bewijzen aan een website wie je bent. immurok haalt de wachtwoordwrijving weg op de machine die voor je staat: scherm ontgrendelen, sudo, beheerdersvragen, SSH- en Git-ondertekening. Een wachtwoordmanager bewaart je wachtwoorden; immurok ontgrendelt 1Password en Bitwarden met een aanraking op macOS en houdt TOTP-seeds op het apparaat, zodat je tweefactorgeheimen niet in een desktop-app staan. Touch ID is Apple's eigen sensor, vastgeklonken aan de Secure Enclave, gesloten voor derden, en bestaat gewoonweg niet op een Mac mini of een extern toetsenbord. immurok is een zelfstandig apparaat: sudo en beheerdersvragen lopen via PAM, een echt systeemmechanisme, en schermontgrendeling gebruikt een apart gedocumenteerde route."),
  ("Heb ik een abonnement nodig?",
   "Nee. Geen abonnement, geen account, geen clouddienst. Je betaalt één keer voor het apparaat. De apps voor macOS, Windows en Linux zijn gratis, en firmware-updates ook. Er stopt niets met werken als je het apparaat nooit met internet verbindt, want dat hoeft niet."),
  ("Hoe reset ik hem, en wat als ik hem kwijtraak?",
   "Houd de knop ongeveer tien seconden ingedrukt voor een fabrieksreset. Het apparaat wist alles: koppelsleutels, elke opgeslagen vingerafdruk en bewaarde inloggegevens, en start opnieuw op, klaar om te koppelen. Dit kun je niet ongedaan maken. Wil je de sleutel naar een andere computer verhuizen zonder alles te wissen, kies dan Ontkoppelen in de app. Raak je hem kwijt, dan kan niemand je vingerafdrukken eruit halen: de sjablonen verlaten de hardware nooit, en de behuizing openbreken activeert een sabotageschakelaar die alles wist en het lampje continu rood laat branden. Elk apparaat heeft een jaar garantie. Het supportadres staat in de handleiding en in de app."),
 ]},

"pl": {
 "og": "pl_PL",
 "name": "Polski",
 "title": "immurok: cena, gdzie kupić i zgodność | Bezprzewodowy klucz z czytnikiem linii papilarnych do Mac, Windows i Linux",
 "desc": "Cena immurok (US$59 na Kickstarterze, US$69 w sprzedaży), gdzie kupić, kraje wysyłki, obsługiwane systemy, bezpieczeństwo, abonament i reset.",
 "lead": "Najczęstsze pytania o immurok wraz z odpowiedziami. Ta sama treść co na stronie angielskiej.",
 "cta": "Wesprzyj na Kickstarterze",
 "back": "Zobacz pełną stronę po angielsku",
 "qa": [
  ("Czym jest immurok?",
   "To niewielki bezprzewodowy klucz z czytnikiem linii papilarnych do komputerów stacjonarnych. Leży na biurku i paruje się przez Bluetooth LE. Jedno dotknięcie odblokowuje ekran, zatwierdza pytania sudo i uprawnienia administratora, podpisuje commity SSH i Git oraz wydaje kody TOTP. Powstał, bo większość komputerów stacjonarnych nie ma czytnika linii papilarnych: Mac mini, Mac Studio, iMac, zamknięty MacBook z zewnętrznym monitorem, dowolna klawiatura zewnętrzna i prawie każdy pecet z Windows lub Linuksem."),
  ("Ile kosztuje immurok?",
   "US$59 na Kickstarterze, US$69 w sprzedaży detalicznej. Płacisz raz. Bez abonamentu i bez opłat za konto. Wysyłka liczona jest osobno przy finalizacji i nie wchodzi w te ceny. Progi early bird na Kickstarterze zostały już wyczerpane."),
  ("Gdzie mogę go kupić i kiedy zostanie wysłany?",
   "Na Kickstarterze, do zakończenia kampanii 22 września 2026 roku. Szacowana dostawa dla wspierających to listopad 2026. Sprzęt jest w szóstej rewizji, a partia pilotażowa 50 sztuk została zbudowana i przetestowana, więc kampania finansuje produkcję seryjną, a nie prototyp. Po kampanii sprzedajemy przez tę stronę."),
  ("Do jakich krajów wysyłacie?",
   "Aktualna lista krajów wysyłki pojawia się przy finalizacji zamówienia na Kickstarterze i to ona jest wiążąca. Wybierz tam swój kraj, a zobaczysz, czy możemy wysłać i ile kosztuje przesyłka. Wysyłka nie jest wliczona we wsparcie. Cła importowe, VAT i opłaty celne pokrywa odbiorca, tak jak zwykle przy sprzęcie z crowdfundingu."),
  ("Z jakimi komputerami i systemami działa?",
   "macOS 13.0 lub nowszy, Windows 10 i 11 oraz większość dystrybucji Linuksa. Aplikacja na Maca to jedna uniwersalna kompilacja dla Apple Silicon i Intela. Windows ma natywne instalatory x64 i Arm64 oraz integrację przez Credential Provider, więc działa na ekranie blokady. Linux to demon w Rust z integracją PAM i polkit, przetestowany na Ubuntu, Fedorze, Archu i Debianie, kompilujący się na większości innych dystrybucji. Ponieważ klucz jest osobnym urządzeniem Bluetooth, a nie czytnikiem wbudowanym w laptopa, działa tak samo z Mac mini, Mac Studio, iMakiem, zamkniętym MacBookiem, klawiaturą zewnętrzną i pecetem. Jeden klucz można powiązać z dwoma komputerami naraz i przełączać się między nimi osobnym palcem."),
  ("Jak to jest zabezpieczone? Gdzie są moje odciski?",
   "W urządzeniu i nigdzie indziej. Wzorce odcisków są przechowywane i porównywane wewnątrz klucza. Nigdy nie trafiają na dysk komputera, do sieci ani do chmury. Przez Bluetooth idzie tylko podpisane HMAC powiadomienie o dopasowaniu, nigdy sam odcisk. Parowanie to bezpośrednia wymiana ECDH między urządzeniem a komputerem. Aktualizacje firmware są podpisane i weryfikowane przed instalacją. Nie ma konta, serwera ani telemetrii: wszystko działa offline i będzie działać, nawet gdyby nas zabrakło."),
  ("Czy to open source?",
   "Cały kod źródłowy jest publiczny na GitHubie, na dwóch różnych licencjach. Aplikacje na macOS, Windows i Linux, wraz z modułami PAM i Credential Providerem dla Windows, są otwarte na licencji Apache 2.0. Firmware i sprzęt są source-available na BSL 1.1 i przechodzą na Apache 2.0 w 2030 roku. Możesz wszystko przeczytać, zmienić, skompilować i wgrać na własne urządzenie. Do czasu konwersji zastrzegamy sobie tylko jedno prawo: sprzedaż konkurencyjnego sprzętu."),
  ("Czym różni się od YubiKey, menedżera haseł albo Touch ID?",
   "To inna warstwa i dobrze się uzupełniają. YubiKey i passkeys dowodzą stronie internetowej, kim jesteś. immurok usuwa mordęgę z hasłem na komputerze, który masz przed sobą: odblokowanie ekranu, sudo, pytania administratora, podpisywanie SSH i Git. Menedżer haseł przechowuje hasła; immurok odblokowuje 1Password i Bitwarden dotknięciem na macOS i trzyma nasiona TOTP w samym urządzeniu, żeby sekrety dwuskładnikowe nie leżały w aplikacji na pulpicie. Touch ID to własny czytnik Apple, zespolony z Secure Enclave, zamknięty dla firm trzecich, a w Mac mini czy klawiaturze zewnętrznej po prostu go nie ma. immurok jest urządzeniem niezależnym: sudo i pytania administratora idą przez PAM, czyli prawdziwy mechanizm systemowy, a odblokowanie ekranu korzysta z osobno udokumentowanej ścieżki."),
  ("Czy potrzebny jest abonament?",
   "Nie. Bez abonamentu, bez konta, bez usługi chmurowej. Płacisz raz za urządzenie. Aplikacje na macOS, Windows i Linux są darmowe, aktualizacje firmware też. Nic nie przestanie działać, jeśli nigdy nie podłączysz urządzenia do internetu, bo nie musi być podłączone."),
  ("Jak go zresetować i co, jeśli go zgubię?",
   "Przytrzymaj przycisk przez około dziesięć sekund, żeby przywrócić ustawienia fabryczne. Urządzenie kasuje wszystko: klucze parowania, wszystkie zapisane odciski i przechowywane poświadczenia, po czym uruchamia się gotowe do ponownego sparowania. Tego nie da się cofnąć. Aby przenieść klucz na inny komputer bez pełnego resetu, wybierz w aplikacji Rozparuj. Jeśli go zgubisz, nikt nie wydobędzie z niego twoich odcisków: wzorce nigdy nie opuszczają sprzętu, a otwarcie obudowy na siłę uruchamia zabezpieczenie, które kasuje wszystko i zostawia diodę świecącą na czerwono. Każde urządzenie ma rok gwarancji. Adres wsparcia znajdziesz w instrukcji i w aplikacji."),
 ]},

"id": {
 "og": "id_ID",
 "name": "Bahasa Indonesia",
 "title": "immurok: harga, cara beli, dan kompatibilitas | Kunci sidik jari nirkabel untuk Mac, Windows, dan Linux",
 "desc": "Harga immurok (US$59 di Kickstarter, US$69 harga ritel), cara membeli, negara pengiriman, sistem yang didukung, keamanan, langganan, dan cara reset.",
 "lead": "Pertanyaan yang paling sering kami terima tentang immurok, beserta jawabannya. Isinya sama dengan situs bahasa Inggris.",
 "cta": "Dukung di Kickstarter",
 "back": "Lihat situs lengkap dalam bahasa Inggris",
 "qa": [
  ("Apa itu immurok?",
   "Kunci sidik jari nirkabel berukuran kecil untuk komputer desktop. Alat ini diletakkan di meja dan dipasangkan lewat Bluetooth LE. Satu sentuhan membuka kunci layar, menyetujui permintaan sudo dan administrator, menandatangani commit SSH dan Git, serta mengeluarkan kode TOTP. Produk ini ada karena sebagian besar komputer desktop tidak punya sensor sidik jari: Mac mini, Mac Studio, iMac, MacBook yang dipakai tertutup dengan monitor eksternal, keyboard eksternal apa pun, dan hampir semua PC Windows atau Linux."),
  ("Berapa harga immurok?",
   "US$59 di Kickstarter dan US$69 harga ritel. Bayar sekali saja. Tidak ada langganan dan tidak ada biaya akun. Ongkos kirim dihitung terpisah saat checkout dan tidak termasuk dalam harga itu. Kuota early bird di Kickstarter sudah habis."),
  ("Di mana bisa membelinya dan kapan dikirim?",
   "Di Kickstarter, sampai kampanye berakhir pada 22 September 2026. Perkiraan pengiriman untuk backer adalah November 2026. Perangkat kerasnya sudah revisi keenam dan satu batch percobaan 50 unit sudah diproduksi dan diuji, jadi dana kampanye dipakai untuk produksi massal, bukan prototipe. Setelah kampanye selesai, penjualan berlanjut lewat situs ini."),
  ("Dikirim ke negara mana saja?",
   "Daftar negara tujuan yang berlaku ditampilkan di halaman checkout Kickstarter, dan daftar itulah yang menjadi acuan. Pilih negara Anda di sana, lalu sistem akan memberi tahu apakah kami bisa mengirim dan berapa ongkos kirimnya. Ongkos kirim tidak termasuk dalam nilai dukungan. Bea masuk, PPN, dan biaya kepabeanan menjadi tanggung jawab penerima, seperti lazimnya perangkat keras hasil crowdfunding."),
  ("Kompatibel dengan komputer dan sistem operasi apa saja?",
   "macOS 13.0 atau lebih baru, Windows 10 dan 11, serta sebagian besar distribusi Linux. Aplikasi Mac berupa satu build universal untuk Apple Silicon dan Intel. Windows punya installer native x64 dan Arm64 dan terintegrasi sebagai Credential Provider, jadi bisa dipakai di layar kunci. Linux berupa daemon Rust dengan integrasi PAM dan polkit, sudah diuji di Ubuntu, Fedora, Arch, dan Debian, dan bisa dikompilasi di kebanyakan distribusi lain. Karena kuncinya adalah perangkat Bluetooth terpisah, bukan sensor yang tertanam di laptop, cara kerjanya sama pada Mac mini, Mac Studio, iMac, MacBook tertutup, keyboard eksternal, maupun PC desktop. Satu kunci bisa terhubung ke dua komputer sekaligus dan berpindah di antaranya lewat sidik jari khusus."),
  ("Seberapa aman? Di mana sidik jari saya disimpan?",
   "Di dalam perangkat, dan tidak di tempat lain. Template sidik jari disimpan dan dicocokkan di dalam kunci itu sendiri. Data itu tidak pernah sampai ke disk komputer, jaringan, atau layanan cloud mana pun. Yang lewat Bluetooth hanya notifikasi bertanda tangan HMAC bahwa sidik jari cocok, bukan sidik jarinya. Pemasangan memakai pertukaran ECDH langsung antara perangkat dan komputer Anda. Pembaruan firmware ditandatangani dan diverifikasi sebelum dipasang. Tidak ada akun, server, maupun telemetri, jadi semuanya berjalan offline dan tetap berjalan meski kami menghilang."),
  ("Apakah open source?",
   "Seluruh kode sumber terbuka di GitHub, dengan dua lisensi berbeda. Aplikasi macOS, Windows, dan Linux, termasuk modul PAM dan Credential Provider untuk Windows, bersifat open source dengan lisensi Apache 2.0. Firmware dan perangkat kerasnya source-available dengan BSL 1.1 dan beralih ke Apache 2.0 pada 2030. Anda bisa membaca semuanya, memodifikasi, membangun sendiri, dan mem-flash ke unit Anda. Satu-satunya hak yang kami tahan sampai peralihan itu adalah menjual perangkat keras pesaing."),
  ("Apa bedanya dengan YubiKey, pengelola kata sandi, atau Touch ID?",
   "Lapisannya berbeda dan justru saling melengkapi. YubiKey dan passkey membuktikan identitas Anda kepada sebuah situs web. immurok menghilangkan repotnya mengetik kata sandi di komputer yang ada di depan Anda: membuka kunci layar, sudo, permintaan administrator, penandatanganan SSH dan Git. Pengelola kata sandi menyimpan kata sandi Anda; immurok membuka kunci 1Password dan Bitwarden dengan satu sentuhan di macOS dan menyimpan seed TOTP di dalam perangkat, sehingga kunci dua faktor Anda tidak menumpuk di aplikasi desktop. Touch ID adalah sensor milik Apple sendiri, menyatu dengan Secure Enclave, tertutup bagi pihak ketiga, dan memang tidak ada di Mac mini atau keyboard eksternal. immurok adalah perangkat mandiri: sudo dan permintaan administrator lewat PAM, mekanisme sistem yang sebenarnya, sedangkan membuka kunci layar memakai jalur bantu yang didokumentasikan terpisah."),
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
 "desc": "immurok 的价格（Kickstarter US$59，零售 US$69）、在哪购买、发货国家、支持的系统、安全性、是否需要订阅以及重置方法。",
 "lead": "关于 immurok 最常被问到的问题和答案。内容与英文站一致。",
 "cta": "在 Kickstarter 上支持",
 "back": "查看完整英文站点",
 "qa": [
  ("immurok 是什么",
   "immurok 是一把用在台式电脑上的小型无线指纹钥匙。它放在桌面上，通过蓝牙 LE 与电脑配对，手指一碰就能解锁屏幕、批准 sudo 和管理员密码提示、给 SSH 和 Git 提交签名、取出 TOTP 验证码。做它是因为大多数台式电脑没有指纹传感器：Mac mini、Mac Studio、iMac、合盖接外接显示器的 MacBook、任何外接键盘，以及几乎所有 Windows 和 Linux 台式机。"),
  ("多少钱",
   "Kickstarter 上 US$59，零售价 US$69。一次性付款，没有订阅费，也没有账号费用。运费不含在内，结算时另算。Kickstarter 的早鸟档已经售罄。"),
  ("在哪买，什么时候发货",
   "现在在 Kickstarter 上，众筹到 2026 年 9 月 22 日结束。支持者的预计发货时间是 2026 年 11 月。硬件已经是第六版，50 台试产做完并测试通过，所以这次的资金用于量产而不是做样机。众筹结束后会在本站销售。"),
  ("发到哪些国家",
   "可发货国家的最新清单显示在 Kickstarter 的结算页面，以那份清单为准。在结算页选择你所在的国家，就能看到能不能发以及运费多少。运费不含在支持金额里。进口关税、增值税和清关费用由收件人承担，这是众筹硬件的通行做法。"),
  ("支持哪些电脑和操作系统",
   "macOS 13.0 及以上、Windows 10 和 11，以及大多数 Linux 发行版。Mac 版是同时支持 Apple Silicon 和 Intel 的通用版本。Windows 版提供 x64 和 Arm64 原生安装包，通过 Credential Provider 集成，所以在锁屏界面上也能用。Linux 版是 Rust 写的守护进程，集成 PAM 和 polkit，在 Ubuntu、Fedora、Arch、Debian 上测试过，多数其他发行版也能编译。因为这把钥匙是独立的蓝牙设备，不是嵌在笔记本里的传感器，所以在 Mac mini、Mac Studio、iMac、合盖的 MacBook、外接键盘和台式 PC 上用法完全一样。一把设备可以同时绑定两台电脑，用一根专门的手指在两者之间切换。"),
  ("安全性如何，指纹存在哪里",
   "存在设备里，别处没有。指纹模板保存在钥匙内部，比对也在钥匙内部完成，不会到你电脑的硬盘、网络或任何云服务上。蓝牙上传输的只是一条用 HMAC 签名的「匹配成功」通知，指纹本身不会出去。配对是设备和电脑之间直接做 ECDH 密钥交换。固件更新经过签名，安装前会验签。没有账号、没有服务器、没有遥测，所以全程离线可用，就算我们哪天不在了它也照样能用。"),
  ("是开源的吗",
   "全部源代码都公开在 GitHub 上，用了两种许可。macOS、Windows 和 Linux 的 App，包括 PAM 模块和 Windows Credential Provider，是 Apache 2.0 的开源软件。固件和硬件是 BSL 1.1 的源码公开许可，2030 年转为 Apache 2.0。你可以读全部代码、修改它、自己编译并烧录到自己的设备上。转换之前我们保留的唯一权利是销售与之竞争的硬件。"),
  ("和 YubiKey、密码管理器、Touch ID 有什么区别",
   "层次不同，可以一起用。YubiKey 和 passkey 解决的是向网站证明你是谁。immurok 解决的是眼前这台电脑上输密码的麻烦：解锁屏幕、sudo、管理员提示、SSH 和 Git 签名。密码管理器保存你的密码；immurok 在 macOS 上可以一碰解锁 1Password 和 Bitwarden，还能把 TOTP 种子存在设备里，这样两步验证的种子就不用躺在桌面 App 中。Touch ID 是苹果自己的传感器，和 Secure Enclave 焊死在一起，第三方用不了，而且 Mac mini 和外接键盘上根本就没有。immurok 是一台独立设备：sudo 和管理员提示走 PAM 这一真实的系统机制，解锁屏幕走另一条单独文档化的辅助路径。"),
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
 "desc": "immurok 的價格（Kickstarter US$59，零售 US$69）、在哪購買、出貨國家、支援的系統、安全性、是否需要訂閱以及重置方法。",
 "lead": "關於 immurok 最常被問到的問題與答案。內容與英文站一致。",
 "cta": "在 Kickstarter 上支持",
 "back": "查看完整英文站點",
 "qa": [
  ("immurok 是什麼",
   "immurok 是一把用在桌上型電腦的小型無線指紋鑰匙。它放在桌面上，透過藍牙 LE 與電腦配對，手指一碰就能解鎖螢幕、核准 sudo 和系統管理員密碼提示、為 SSH 與 Git 提交簽章、取出 TOTP 驗證碼。會做它是因為大多數桌上型電腦沒有指紋感測器：Mac mini、Mac Studio、iMac、闔蓋外接螢幕的 MacBook、任何外接鍵盤，以及幾乎所有 Windows 和 Linux 桌機。"),
  ("多少錢",
   "Kickstarter 上 US$59，零售價 US$69。一次付清，沒有訂閱費，也沒有帳號費用。運費不含在內，結帳時另計。Kickstarter 的早鳥檔次已經售完。"),
  ("在哪買，什麼時候出貨",
   "現在在 Kickstarter 上，募資到 2026 年 9 月 22 日結束。支持者的預計出貨時間是 2026 年 11 月。硬體已經是第六版，50 台試產完成並通過測試，所以這次的資金用於量產而不是做原型。募資結束後會在本站販售。"),
  ("寄到哪些國家",
   "可出貨國家的最新清單顯示在 Kickstarter 的結帳頁面，以那份清單為準。在結帳頁選擇你所在的國家，就能看到能不能寄以及運費多少。運費不含在支持金額裡。進口關稅、加值稅和報關費用由收件人負擔，這是群眾募資硬體的通行做法。"),
  ("支援哪些電腦和作業系統",
   "macOS 13.0 以上、Windows 10 和 11，以及大多數 Linux 發行版。Mac 版是同時支援 Apple Silicon 和 Intel 的通用版本。Windows 版提供 x64 和 Arm64 原生安裝程式，透過 Credential Provider 整合，所以在鎖定畫面上也能用。Linux 版是用 Rust 寫的常駐程式，整合 PAM 和 polkit，在 Ubuntu、Fedora、Arch、Debian 上測試過，多數其他發行版也能編譯。因為這把鑰匙是獨立的藍牙裝置，不是嵌在筆電裡的感測器，所以在 Mac mini、Mac Studio、iMac、闔蓋的 MacBook、外接鍵盤和桌機上用法完全一樣。一把裝置可以同時綁定兩台電腦，用一根專門的手指在兩者之間切換。"),
  ("安全性如何，指紋存在哪裡",
   "存在裝置裡，別的地方都沒有。指紋範本儲存在鑰匙內部，比對也在鑰匙內部完成，不會傳到你電腦的硬碟、網路或任何雲端服務。藍牙上傳輸的只是一則用 HMAC 簽章的「比對成功」通知，指紋本身不會出去。配對是裝置和電腦之間直接做 ECDH 金鑰交換。韌體更新都有簽章，安裝前會驗證。沒有帳號、沒有伺服器、沒有遙測，所以全程離線可用，就算我們哪天不在了也照樣能用。"),
  ("是開源的嗎",
   "全部原始碼都公開在 GitHub 上，採用兩種授權。macOS、Windows 和 Linux 的應用程式，包含 PAM 模組和 Windows Credential Provider，是 Apache 2.0 的開源軟體。韌體和硬體採 BSL 1.1 的原始碼公開授權，2030 年轉為 Apache 2.0。你可以讀全部程式碼、修改它、自己編譯並燒錄到自己的裝置上。轉換之前我們保留的唯一權利是販售與之競爭的硬體。"),
  ("和 YubiKey、密碼管理器、Touch ID 有什麼差別",
   "層次不同，可以一起用。YubiKey 和 passkey 解決的是向網站證明你是誰。immurok 解決的是眼前這台電腦上輸入密碼的麻煩：解鎖螢幕、sudo、系統管理員提示、SSH 和 Git 簽章。密碼管理器保存你的密碼；immurok 在 macOS 上可以一碰解鎖 1Password 和 Bitwarden，還能把 TOTP 種子存在裝置裡，這樣兩步驟驗證的種子就不用躺在桌面應用程式中。Touch ID 是蘋果自家的感測器，和 Secure Enclave 綁死在一起，第三方用不了，而且 Mac mini 和外接鍵盤上根本就沒有。immurok 是一台獨立裝置：sudo 和系統管理員提示走 PAM 這個真實的系統機制，解鎖螢幕走另一條單獨記錄在文件裡的輔助路徑。"),
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
        <a href="{ks}?ref=immurok_site_{code}" target="_blank" rel="noopener" class="btn btn-primary btn-sm">{cta}</a>
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
           navlogo=NAV_LOGO, back=e(data["back"]), ks=KS, cta=e(data["cta"]),
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
