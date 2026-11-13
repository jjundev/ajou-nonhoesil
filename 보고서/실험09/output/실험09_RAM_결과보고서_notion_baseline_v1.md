<table_of_contents color="gray"/>
<empty-block/>
# 실험 결과
## 실험 1) 2bit RAM
74HC00 두 개로 A와 B의 NAND SR Latch를 하나씩 만들고, 74HC03의 네 게이트로 두 읽기 출력단을 만든 회로다. 저장되는 값은 WR1과 같고, 출력은 OUT0=OE0·(A의 Q), OUT1=OE1·(B의 Q)다. A에 1, B에 0, B에 1, A에 0을 차례로 쓰고 쓸 때마다 IN을 내려 저장한 뒤 OE를 올려 읽었다.
- **2bit RAM 쓰기·읽기**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>OE0</td>
<td>IN0</td>
<td>WR0</td>
<td>OE1</td>
<td>IN1</td>
<td>WR1</td>
<td>OUT0</td>
<td>OUT1</td>
</tr>
<tr>
<td>S1</td>
<td>모든 입력을 GND에 두고 WR1만 +5V에 둔 채 전원을 켠다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W1</td>
<td>A에 1 쓰기: IN0을 +5V로 올린다</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R1</td>
<td>IN0을 GND로 내려 저장한 뒤 OE0을 +5V로 올려 A를 읽는다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>W2</td>
<td>B에 0 쓰기: OE0을 내리고 WR0을 +5V, WR1을 GND로 바꾼 뒤 IN1을 올린다</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R2</td>
<td>IN1을 내려 저장한 뒤 OE0·OE1을 올려 A·B를 읽는다</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>W3</td>
<td>B에 1 쓰기: OE0·OE1을 내리고 WR0을 GND, WR1을 +5V로 바꾼 뒤 IN1을 올린다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R3</td>
<td>IN1을 내려 저장한 뒤 OE0·OE1을 올려 A·B를 읽는다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>W4</td>
<td>A에 0 쓰기: OE0·OE1을 내리고 WR0을 +5V, WR1을 GND로 바꾼 뒤 IN0을 올린다</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R4</td>
<td>IN0을 내려 저장한 뒤 OE0·OE1을 올려 A·B를 읽는다</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
	</table>
아홉 스텝 모두 예상과 일치했다. 쓰는 동안에는 OE를 내려 두었기 때문에 두 LED가 모두 꺼져 있었고, IN을 내린 뒤 OE를 올리자 그때 저장된 값이 LED에 나왔다. B에 0을 쓴 뒤 읽었을 때는 OUT0만 켜져 있어, 앞서 A에 쓴 1이 B를 쓰는 동안에도 남아 있었다. B에 1을 쓴 뒤에는 두 LED가 함께 켜졌고, 마지막으로 A에 0을 쓰자 OUT0만 꺼지고 OUT1은 켜진 채로 남았다. 한쪽에 쓰는 동안 다른 쪽 값이 바뀐 경우는 없었다.
실험 도중 전원 공급기가 CC 모드로 넘어간 일이 한 번 있었고, B에 1을 쓰기 전에 선 하나가 빠져 다시 꽂았다. 두 경우 모두 원인을 바로잡은 뒤의 결과가 위 표이며, 경위는 결과 분석에 적었다.
<empty-block/>
## 실험 2) 16bit RAM (IC 74670)
74670 하나로 구성하고 출력 Q1\~Q4에 LED를 단 회로다. 주소는 B, A 순서로 적고 데이터는 D4 D3 D2 D1 순서로 적었다. 주소 00, 01, 10, 11에 0001, 0010, 0100, 1000을 쓰는 동안에는 RE를 1로 두어 출력을 껐고, 쓰기를 마친 뒤 RE를 0으로 내리고 읽기 주소를 바꿔 가며 네 word를 읽었다.
- **16bit RAM 쓰기 입력**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>WB</td>
<td>WA</td>
<td>WE</td>
<td>D4</td>
<td>D3</td>
<td>D2</td>
<td>D1</td>
</tr>
<tr>
<td>S1</td>
<td>WE·RE를 +5V, 나머지를 GND에 둔 뒤 D1만 +5V로 옮기고 전원을 켠다(주소 00, 데이터 0001)</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>W1</td>
<td>WE를 GND로 내려 주소 00에 0001을 쓴다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>A2</td>
<td>WE를 먼저 +5V로 올린 뒤 주소 01, 데이터 0010으로 바꾼다</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>W2</td>
<td>WE를 GND로 내려 주소 01에 쓴다</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>A3</td>
<td>WE를 먼저 올린 뒤 주소 10, 데이터 0100으로 바꾼다</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W3</td>
<td>WE를 GND로 내려 주소 10에 쓴다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>A4</td>
<td>WE를 먼저 올린 뒤 주소 11, 데이터 1000으로 바꾼다</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W4</td>
<td>WE를 GND로 내려 주소 11에 쓴다</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>H1</td>
<td>WE를 +5V로 올려 쓰기를 끝낸다</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R1</td>
<td>RE를 GND로 내려 주소 00을 읽는다</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R2</td>
<td>RA를 +5V로 옮겨 주소 01을 읽는다</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R3</td>
<td>RB를 +5V, RA를 GND로 옮겨 주소 10을 읽는다</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R4</td>
<td>RA를 +5V로 옮겨 주소 11을 읽는다</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
- **16bit RAM 읽기 입력과 출력**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>RB</td>
<td>RA</td>
<td>RE</td>
<td>Q4</td>
<td>Q3</td>
<td>Q2</td>
<td>Q1</td>
</tr>
<tr>
<td>S1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>A2</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W2</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>A3</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W3</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>A4</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>W4</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>H1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>R2</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>R3</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R4</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
열세 스텝 모두 예상과 일치했다. 네 번 쓰는 동안 LED는 계속 꺼져 있었고, RE를 내리자 주소 00에서 Q1이 켜졌다. 이후 읽기 주소를 01, 10, 11로 옮길 때마다 켜지는 LED가 Q2, Q3, Q4로 하나씩 옮겨 가, 주소마다 쓴 값이 따로 남아 있었다. 다만 주소 01에서 10으로 옮기는 동안 Q4가 약 6초 동안 혼자 켜졌다가 Q3으로 넘어갔다. 두 주소 비트를 바꾸는 사이에 생긴 중간 상태로 보이며, 결과 분석에서 다루었다.
<empty-block/>
<empty-block/>
# 실험 사진
항목마다 예비보고서에서 그린 결선도를 먼저 싣고, 그 아래에 실험을 촬영한 영상에서 장면을 골라 한 장에 모았다. 사진마다 LED가 보이도록 회로 부분만 잘랐고, 위의 띠에는 그 장면에서 읽은 값과 켜진 LED를 적었다. 실험 1에서는 위 LED가 OUT0, 아래 LED가 OUT1이고, 실험 2에서는 위에서부터 Q1, Q2, Q3, Q4다.
<empty-block/>
## 실험 1) 2bit RAM
![예비보고서에서 그린 2bit RAM 결선도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/d55f08ca-6649-4609-818d-5ba97e73e080/%EC%8B%A4%ED%97%9809_1_%EC%86%90%EA%B7%B8%EB%A6%BC_2bitRAM.png)
![2bit RAM에서 쓰기를 마칠 때마다 A·B를 읽은 네 장면](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/c7215f46-d906-4c2e-bb45-55b613c28fce/%EC%8B%A4%ED%97%9809_1_%EC%82%AC%EC%A7%84_2bitRAM.jpg)
<empty-block/>
## 실험 2) 16bit RAM (IC 74670)
![예비보고서에서 그린 16bit RAM 결선도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/ea94b020-5c45-4358-a796-ce062aeb7bd5/%EC%8B%A4%ED%97%9809_2_%EC%86%90%EA%B7%B8%EB%A6%BC_16bitRAM.png)
![74670에 쓰는 동안의 꺼진 상태와 네 주소를 읽은 장면. 주소 01에서 10으로 옮기는 중간에 Q4가 켜진 장면을 함께 실었다](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/f7582b20-809d-4bfb-8e31-f4742d6367ad/%EC%8B%A4%ED%97%9809_2_%EC%82%AC%EC%A7%84_16bitRAM.jpg)
<empty-block/>
<empty-block/>
# 예비보고서와의 비교
실험 1은 예비보고서에서 회로도를 따라 세운 예상대로 저장값이 WR1을 따랐고, 출력은 OE를 올린 쪽에서만 나왔다. 예비보고서에서는 강의노트 범례가 WR0을 A의 값, WR1을 B의 값으로 적은 것과 달리 회로도에서는 두 선이 A와 B 양쪽 래치에 함께 들어간다고 보고 쓰는 순서를 정했는데, 그 순서대로 A와 B에 각각 0과 1을 써서 모두 맞게 읽혔으므로 회로도를 읽은 방식이 맞았다고 본다.
예비보고서에서 걱정한 LED 밝기도 문제가 되지 않았다. 74HC03은 출력 1을 10kΩ 풀업으로 만들기 때문에 LED 전류가 약 0.29mA로 작아 어둡게 켜질 수 있다고 보았는데, 실제로는 켜진 LED와 꺼진 LED가 눈으로 충분히 구분됐다.
실험 2는 네 주소에 다른 LED 하나가 켜지도록 값을 골라 둔 덕분에, 읽은 결과만으로 주소 선택과 데이터선 D1\~D4, 출력 Q1\~Q4가 모두 맞게 이어졌음을 확인할 수 있었다. 예비보고서에서 주소를 바꾸기 전에 WE를 먼저 올리기로 한 것도 그대로 지켰고, 다른 주소의 값이 덮어써진 흔적은 없었다. 읽기 주소를 바꾸는 도중 잠깐 다른 word가 나온 장면이 있었지만, 두 주소 비트를 한 번에 바꿀 수 없어 생기는 중간 상태라 예상할 수 있는 범위였다.
<empty-block/>
<empty-block/>
# 결과 분석
실험 1의 각 래치는 IN이 0이면 S'와 R'가 모두 1이 되어 값을 유지하고, IN이 1일 때만 WR1과 WR0 중 1인 쪽으로 세트 또는 리셋된다. WR은 A와 B에 공통이지만 IN0과 IN1을 동시에 올리지 않았기 때문에, 한 번에 IN을 올린 쪽 래치만 바뀌고 다른 쪽은 그대로 남았다. 쓰는 동안 LED가 꺼져 있던 것은 OE를 0으로 두어 74HC03 출력단이 OE·Q=0을 냈기 때문이고, 쓰기를 마친 뒤 IN을 먼저 내리고 OE를 올렸으므로 LED에는 WR 입력이 아니라 래치에 저장된 값이 나왔다. 마지막 읽기에서 OUT1만 켜진 것이 이를 보여 준다. 그때 WR1은 0이었으므로 WR이 그대로 출력됐다면 OUT1도 꺼져 있어야 했다.
실험 1 도중 전원 공급기가 CC 모드로 넘어간 것은 칩의 VCC 선을 GND 레일로 옮겼기 때문이다. VCC 선이 입력선과 같은 색이어서 입력을 바꾸려다 그 선을 입력선으로 착각했고, 선을 제자리에 다시 꽂자 전원이 정상으로 돌아와 회로가 동작했다. 이 회로에서는 IN, WR, OE 입력과 다른 칩의 출력이 각 칩의 입력 핀에 5V를 걸고 있으므로, 한 칩의 VCC 핀이 GND에 붙으면 그 칩의 입력 보호 다이오드를 거쳐 +5V에서 GND로 큰 전류가 흐를 수 있다. 이 전류가 전원 공급기에 설정된 전류 제한을 넘어 CC 모드로 바뀐 것으로 보인다. 어느 칩의 VCC 선이었는지와 그때 흐른 전류는 확인하지 못했다.
B에 1을 쓰기 전에는 선 하나가 빠진 것을 발견해 다시 꽂았다. 어느 선이었는지는 확인하지 못했다. 그 직전의 읽기는 예상대로 나왔고, 다시 꽂은 뒤 B에 1을 쓴 단계부터 끝까지도 모두 예상과 같았다.
실험 2의 74670은 쓰기 쪽과 읽기 쪽 주소가 따로 있는 레지스터 파일이다. RE=1인 동안 출력이 고임피던스가 되므로 쓰는 동안 LED에 전류가 흐르지 않아 모두 꺼져 있었다. 쓰기는 WE가 0인 동안 WB·WA가 고른 word가 D1\~D4를 따라가는 방식이라, WE를 1로 올린 뒤에 주소와 데이터를 바꿨기 때문에 바꾸는 도중의 값이 다른 word로 들어가지 않았다. 읽은 네 word가 각각 0001, 0010, 0100, 1000으로 서로 겹치지 않았으므로 의도한 주소에만 써졌다고 본다.
주소 01에서 10으로 옮기는 동안 Q4가 켜진 것은 RB와 RA를 바꾼 순서 때문으로 보인다. SN74LS670 데이터시트의 논리도를 보면 읽기 쪽은 RB·RA를 디코드해 네 word 중 하나를 AND-OR로 골라 내보내는 조합 회로라, 저장된 값과 관계없이 주소 입력이 바뀌는 즉시 출력이 따라간다. 01에서 10으로 가려면 두 비트를 모두 바꿔야 하는데, RB를 먼저 올리고 RA를 나중에 내렸다면 그 사이에 주소가 잠깐 11이 되어 word 3의 1000, 곧 Q4가 나온다. 켜진 LED가 주소 11을 읽을 때와 같은 Q4였다는 점이 이 해석과 맞는다. 다만 실제로 두 스위치를 어떤 순서로 바꿨는지는 확인하지 못했다. 이 중간 상태는 스위치를 손으로 옮긴 시간만큼 이어진 것이라 LED로도 보였다. 읽기 순서를 00, 01, 11, 10처럼 한 번에 한 비트만 바뀌게 잡거나, 주소를 바꾸는 동안 RE를 1로 올려 출력을 꺼 두면 다른 word가 나오는 일을 막을 수 있다.
<empty-block/>
<empty-block/>
# 고찰
이번 실험의 목적은 RAM의 쓰기와 읽기 동작을 이해하는 것이었다. 2bit RAM에서는 A와 B에 0과 1을 따로 써서 쓴 값이 그 비트에만 저장되고 다른 비트는 유지되는 것을 확인했고, 74670에서는 네 주소에 쓴 4bit 값이 주소마다 따로 읽히는 것을 확인했다. 두 실험 모두 모든 스텝이 예상과 일치했으므로 목적은 달성했다고 본다.
실험 1에서 막혔던 것은 두 가지다. 전원 공급기가 CC 모드로 넘어갔는데, 입력선과 같은 색이던 칩의 VCC 선을 입력선으로 착각해 GND 레일로 옮겼던 것이 원인이었다. 또 B에 1을 쓸 준비를 하다가 선 하나가 빠졌는데, 어느 선이었는지는 확인하지 못했다. 스텝마다 읽은 결과는 두 실험 모두 예상과 같았다.
VCC 선을 제자리에 다시 꽂자 정상으로 동작했고, 빠진 선은 다시 꽂은 뒤 B에 1을 쓰는 단계부터 이어서 진행했다. 두 일의 경위와 원인은 결과 분석에 적었다.
새로 알게 된 점은 전원선과 입력선이 같은 색이면 입력을 옮기다가 전원선을 잘못 건드릴 수 있다는 것이다.
<empty-block/>
<empty-block/>
# 추가 공부
## 전원 공급기의 CC 모드와 전원핀이 접지된 CMOS 칩
실험실에서 쓰는 전원 공급기는 전압 설정값과 전류 제한값을 함께 가진다. 부하에 흐르는 전류가 전류 제한값보다 작으면 출력 전압을 설정값으로 유지하는 CV(정전압) 모드로 동작하고, 부하 저항이 작아져 설정 전압에서 흘러야 할 전류가 제한값을 넘으면 전류를 제한값에 묶어 두는 CC(정전류) 모드로 바뀐다. CC 모드에서 출력 전압은 제한 전류와 부하 저항의 곱으로 정해지므로, +5V와 GND 사이가 거의 단락된 상태라면 표시 전압이 크게 떨어진다. 실험 중 CC 표시가 켜졌다는 것은 회로 어딘가에 +5V에서 GND로 가는 낮은 저항 경로가 생겼다는 신호다.
CMOS 칩의 입력 핀에는 정전기 보호를 위해 입력에서 VCC 쪽과 GND 쪽으로 각각 다이오드가 달려 있다. 평소에는 입력 전압이 0과 VCC 사이에 있어 두 다이오드가 모두 꺼져 있지만, VCC 핀이 GND에 붙은 상태에서 입력에 5V가 걸리면 입력에서 VCC 쪽으로 가는 다이오드가 켜진다. 그러면 5V 입력선, 보호 다이오드, 접지된 VCC 핀을 거쳐 전류가 흐르고, 입력 점퍼가 여러 개 5V에 꽂혀 있으면 그 전류가 더해진다. 이번 실험의 CC 전환도 이 경로로 설명할 수 있다고 본다. 이렇게 흐르는 전류는 보호 다이오드의 허용 전류를 넘을 수 있어 칩을 상하게 할 수도 있다. 74HC 계열의 입력 보호 다이오드 허용 전류는 데이터시트 확인이 필요하다.
전류 제한값을 회로가 실제로 쓰는 전류보다 조금만 높게 두면, 이런 실수가 생겼을 때 전원 공급기가 곧바로 CC로 넘어가 흐르는 전류를 묶어 두므로 칩을 보호할 수 있다. 예를 들어 실험 2는 74670 하나만 쓰는데, SN74LS670 데이터시트의 전원 전류 ICC는 전형 30mA, 최대 50mA다. 여기에 LED 전류를 더한 값보다 약간 높게 제한을 두면 정상 동작에는 영향이 없다. 전원선을 빨간색, GND선을 검은색으로 정해 두고 입력선에는 다른 색을 쓰는 것도 같은 실수를 줄이는 방법이다.
<empty-block/>
## 74670 출력의 LED 구동
SN74LS670의 권장 동작 조건에서 출력이 1일 때 내보낼 수 있는 전류 IOH는 최대 2.6mA이고, 이 전류에서 출력 전압 VOH는 최소 2.4V로 보증되고, 전형값은 3.1V다. 출력을 GND에 단락했을 때의 전류 IOS는 30mA에서 130mA 사이이고, 한 번에 출력 하나만 1초를 넘지 않게 단락하도록 적혀 있다.
이번 회로는 출력 → LED → 330Ω → GND로 이어져 있다. 330Ω에 2.6mA가 흐르려면 저항 양단에 2.6mA × 330Ω ≈ 0.86V가 걸려야 하므로, 출력 전압이 LED 순방향 전압보다 0.86V 이상 높아야 한다. 예비보고서처럼 LED 순방향 전압을 2V로 잡으면 필요한 출력 전압은 약 2.86V로, 보증된 최소 2.4V보다 높고 전형 3.1V보다는 낮다. 따라서 출력 전압이 전형값 근처라면 LED 전류는 권장 한도인 2.6mA를 조금 넘는 수준이 되고, 그만큼 출력 전압이 내려가면서 전류가 스스로 줄어든다. 단락 전류 최소값 30mA보다는 한참 작으므로 칩이 상할 수준은 아니다. 이번 실험에서 LED 순방향 전압과 출력 전압은 측정하지 않았다.
실험 1의 LED는 74HC03의 출력이 꺼질 때 10kΩ 풀업을 거쳐 켜지므로 약 0.29mA밖에 흐르지 않는다. 실험 2의 LED에는 이보다 열 배 가까이 큰 mA 단위의 전류가 흐르므로, 계산대로라면 실험 2의 LED가 더 밝게 켜진다. 다만 위 수치는 SN74LS670의 것이고, 강의노트는 74670의 계열을 적지 않았다. 실제로 받은 칩이 다른 계열이라면 출력 전류 한도가 다를 수 있어 실물 칩의 각인과 그 제조사 데이터시트로 확인이 필요하다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Nexperia. 74HC00; 74HCT00 — Quad 2-input NAND gate. Rev. 11, 2025-04-29. [https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf)
- Nexperia. 74HC03; 74HCT03 — Quad 2-input NAND gate (open drain). Rev. 7, 2024-02-16. [https://assets.nexperia.com/documents/data-sheet/74HC_HCT03.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT03.pdf)
- Texas Instruments. SN54LS670, SN74LS670, 4-by-4 Register Files with 3-State Outputs. 문서번호 SDLS193, 1974-03 발행, 1988-03 개정. [https://www.ti.com/lit/ds/symlink/sn74ls670.pdf](https://www.ti.com/lit/ds/symlink/sn74ls670.pdf)