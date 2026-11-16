
#折现图
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import seaborn as sns
import  numpy as np

sns.set(style="whitegrid")

x=np.linspace(0,10,100)
y1=np.sin(x)
y2=np.cos(x)

plt.figure(figsize=(10,6))
plt.plot(x,y1,label="Sine Wave",color="b",linewidth=2)
plt.plot(x,y2,label="Cosine Wave",color="r",linestyle="-",linewidth=2)

plt.fill_between(x,y1,y2,color="gray",alpha=0.1)
plt.title("Line Plot",fontsize=15)
plt.xlabel("X-axis",fontsize=12)
plt.ylabel("Y-axis",fontsize=12)
plt.legend()
plt.show()


#散点图
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import seaborn as sns
import  numpy as np

sns.set(style="whitegrid")

x=np.random.rand(100)
y=np.random.rand(100)
colors=np.random.rand(100)
sizes=1000*np.random.rand(100)

plt.figure(figsize=(10,6))
plt.scatter(x,y,c=colors,s=sizes,alpha=0.5,cmap='viridis')
plt.colorbar()

plt.title("Scattrt Plot",fontsize=15)
plt.xlabel("X-axis",fontsize=12)
plt.ylabel("Y-axis",fontsize=12)
plt.show()


#条形图
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style="whitegrid")
categories=['A','B','C','D']
value1=[5,7,8,6]
value2=[3,4,5,2]

fig,ax=plt.subplots(figsize=(10,6))
bar1=ax.bar(categories,value1,label='Group 1')
bar2=ax.bar(categories,value2,bottom=value1,label='Group 2')

ax.set_title("Stacked Bar Chart",fontsize=15)
ax.set_xlabel("Categories",fontsize=12)
ax.set_ylabel("Value",fontsize=12)
ax.legend()

for rect in bar1 + bar2:
    height=rect.get_height()
    ax.annotate(f'{height}',xy=(rect.get_x()+rect.get_width()/2,height),
                xytext=(0,3),textcoords="offset points",ha='center',va='bottom')

plt.show()


#热力图
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import seaborn as sns
import  numpy as np

#生成数据
data = np.random.rand(10,12)
#创建热图
plt.figure(figsize=(10,6))
sns.heatmap(data,annot=True,fmt=".2f",cmap='coolwarm')
#添加装饰
plt.title("Heatmap",fontsize=15)
plt.show()

