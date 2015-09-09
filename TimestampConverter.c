#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

#define SECsince1970            946684800
#define SECbyYEAR               31536000
#define SECbyDAY                86400
#define SECbyHOUR               3600
#define SECbyMIN                60


/**
 * @brief Fills a time structure from a timestamp
 */
int common_calcDate(uint32_t stamp, struct tm* tm)
{
    int year;
    uint32_t mystamp = stamp;
    uint16_t *monthsinyear;
    uint16_t monthsinnorm[] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365};
    uint16_t monthsinleap[] = {0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366};

    uint16_t WDayMonNorm[] = {0, 0, 3, 3, 6, 1, 4, 6, 2, 5, 0, 3, 5};
    uint16_t WDayMonLeap[] = {0, 6, 2, 3, 6, 1, 4, 6, 2, 5, 0, 3, 5};

    int i;
    uint16_t myWday = 0;

    if(tm == NULL)
    {
        return -1;
    }

    mystamp -= SECsince1970; //seconds since 01/01/2000 00:00:00

    tm->tm_sec = (int) (mystamp % 60);
    mystamp = mystamp / 60;

    tm->tm_min = (int) (mystamp % 60);
    mystamp = mystamp / 60;

    tm->tm_hour = (int) (mystamp % 24);
    mystamp = mystamp / 24;

    //Number of days since 01/01/2000
    year = 2000;
    while(mystamp >= 365)
    {
        if((year%4 == 0 && year%100 != 0) || year%400 == 0) //Leap year
        {
            if(mystamp == 365)
            {
                break;
            }

            mystamp -= 366;
        }
        else
        {
            mystamp -= 365;
        }
        year += 1;
    }
    tm->tm_year = year-2000; //Years corrected with leap days

    //Calculate month and days.
    if((year%4 == 0 && year%100 != 0) || year%400 == 0) //Leap year
    {
        monthsinyear = monthsinleap;
    }
    else
    {
        monthsinyear = monthsinnorm;
    }
    for(i=1; i<=12; i++)
    {
        if(mystamp < monthsinyear[i])
        {
            tm->tm_mon = i;
            mystamp = mystamp - monthsinyear[i-1];
            break;
        }
    }
    
    tm->tm_mday = (int)(mystamp) + 1;

    // Calculate week day
    if((year%4 == 0 && year%100 != 0) || year%400 == 0)
    {
        //Leap year
        myWday = WDayMonLeap[tm->tm_mon];
    }
    else
    {
        //Normal year
        myWday = WDayMonNorm[tm->tm_mon];
    }

    myWday += tm->tm_mday + tm->tm_year + (tm->tm_year / 4) + 6;
    myWday %= 7;

    tm->tm_wday = myWday; //1 - Mon, 2 - Tue, ... 6 - Sat, 0 - Sun

    return 0;
}


/**
 * @brief Calculates a timestamp from a common date
 */
uint32_t common_calcTimestamp(uint32_t year, uint32_t month, uint32_t day, uint32_t hour, uint32_t minute, uint32_t second)
{
 	//TODO verify if leap years are managed

 	uint32_t stamp = 0;
 	uint32_t i;

 	stamp = SECsince1970;

 	stamp += year * SECbyYEAR;

 	if((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) // Not leap year
    {
        stamp += ((year / 4) * SECbyDAY); //Adds February 29ths
    }
    else
    {
        stamp += (((year / 4) + 1) * SECbyDAY);  //Adds February 29ths
 	}

 	i = month-1;
 	while(i > 0)
 	{
 		if(i == 1 || i == 3 || i == 5 || i == 7 || i == 8 || i == 10 || i == 12)
        {
            stamp += (31 * SECbyDAY);
        }
        else if(i == 2)
        {
            if(year%4 != 0)
            {
                stamp += (28*SECbyDAY);
            }
            else
            {
                stamp += (29*SECbyDAY);
            }
        }
        else
        {
            stamp += (30 * SECbyDAY);
        }

        i -= 1;
 	}

 	stamp += (day-1) * SECbyDAY;
 	stamp += hour * SECbyHOUR;
 	stamp += minute * SECbyMIN;
 	stamp += second;

 	return stamp;
 }

 int main()
 {
    uint32_t i, r;
    struct tm t;

    for(i=1262307661; i<4294967296; i++)
    {
        if(i%10000000 == 0)
        {
            printf("Made up to %u (%X) \n", i, i);
        }

        common_calcDate(i, &t);
        r = common_calcTimestamp(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec);

        if(r != i)
        {
            printf("ERROR : %u (%X) != %u (%X) (!!!!) \n", i, i, r, r);
            common_calcDate(i, &t);
            printf("%d/%d/%d %d:%d:%d \n", t.tm_mday, t.tm_mon, t.tm_year, t.tm_hour, t.tm_min, t.tm_sec);
            common_calcTimestamp(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec);

            return -1;
        }
    }

    printf("All dates OK!\n");

    return 0;
 }